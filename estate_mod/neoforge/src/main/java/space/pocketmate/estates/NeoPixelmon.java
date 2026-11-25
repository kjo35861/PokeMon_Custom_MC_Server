package space.pocketmate.estates;

import java.util.*;
import net.minecraft.nbt.NbtCompound;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.neoforged.bus.api.*;
import net.neoforged.fml.ModList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Optional Pixelmon 9.4.3 bridge. The Fabric build does not load this class. */
final class NeoPixelmon {
    private static final String PREFIX = "com.pixelmonmod.pixelmon.";
    private static final String NATURAL = "pocketmate_natural_spawn";
    private static final Logger LOG = LoggerFactory.getLogger("pocketmate-pixelmon");
    private static final Map<MinecraftServer,ArrayDeque<Runnable>> CAPTURES = new IdentityHashMap<>();
    private static final Map<Object,UUID> BATTLES = new WeakHashMap<>();

    static void register() {
        if (!ModList.get().isLoaded("pixelmon")) return;
        try {
            IEventBus bus = (IEventBus) type("Pixelmon").getField("EVENT_BUS").get(null);
            listen(bus,"spawning.SpawnEvent",NeoPixelmon::spawned);
            listen(bus,"CaptureEvent$SuccessfulCapture",NeoPixelmon::captured);
            listen(bus,"battles.BattleEndEvent",NeoPixelmon::battleEnded);
            listen(bus,"ExperienceGainEvent",NeoPixelmon::experience);
            listen(bus,"LevelUpEvent$Post",NeoPixelmon::leveled);
            NeoEvents.afterTick(server -> {
                var work = CAPTURES.remove(server);
                if (work != null) work.forEach(Runnable::run);
            });
            NeoEvents.stopped(server -> { CAPTURES.remove(server); BATTLES.clear(); });
            MissionsMod.connectPokemon();
            LOG.info("Pixelmon capture, battle, training and first-capture titles connected");
        } catch (ReflectiveOperationException | RuntimeException | LinkageError e) {
            LOG.error("Pixelmon bridge initialization failed",e);
        }
    }
    interface Handler { void accept(Event event) throws Exception; }
    private static void listen(IEventBus bus,String name,Handler handler) throws ReflectiveOperationException {
        Class<? extends Event> event = type("api.events."+name).asSubclass(Event.class);
        // Explicit event class avoids generic inference from a reflective handler.
        bus.addListener(EventPriority.LOWEST,false,event,e -> guarded(() -> {
            if (MissionsMod.pokemonReady() && (!(e instanceof ICancellableEvent c) || !c.isCanceled())) handler.accept(e);
        }));
    }
    interface Work { void run() throws Exception; }
    private static void guarded(Work work) {
        try { work.run(); }
        catch (Exception | LinkageError error) { LOG.warn("Pixelmon event could not be recorded",error); }
    }
    private static Class<?> type(String suffix) throws ClassNotFoundException { return Class.forName(PREFIX+suffix); }
    private static Object get(Object target,String name) throws ReflectiveOperationException { return target.getClass().getMethod(name).invoke(target); }
    private static Object field(Object target,String name) throws ReflectiveOperationException { return target.getClass().getField(name).get(target); }
    private static UUID uuid(Object pokemon) throws ReflectiveOperationException { return (UUID)get(pokemon,"getUUID"); }
    private static int dex(Object pokemon) throws ReflectiveOperationException { return (Integer)get(get(pokemon,"getSpecies"),"getDex"); }
    private static NbtCompound data(Object pokemon) throws ReflectiveOperationException { return (NbtCompound)get(pokemon,"getPersistentData"); }
    private static boolean natural(Object pokemon) throws ReflectiveOperationException {
        return data(pokemon).getBoolean(NATURAL) && get(pokemon,"getOriginalTrainerUUID")==null;
    }
    private static void spawned(Event event) throws Exception {
        Object spawner=field(event,"spawner"),action=field(event,"action");
        if (!Set.of(PREFIX+"spawning.PlayerTrackingSpawner",PREFIX+"spawning.LegendarySpawner").contains(spawner.getClass().getName())
                || !type("api.spawning.archetypes.entities.pokemon.SpawnActionPokemon").isInstance(action)) return;
        Object entity=get(action,"getOrCreateEntity");
        if (entity != null) data(get(entity,"getPokemon")).putBoolean(NATURAL,true);
    }
    private static void captured(Event event) throws Exception {
        if (!(get(event,"getPlayer") instanceof ServerPlayerEntity player) || player.isCreative() || player.isSpectator()) return;
        Object pokemon=get(event,"getPokemon");
        if (!natural(pokemon)) return;
        MinecraftServer server=player.getServer();
        if (server==null) return;
        CAPTURES.computeIfAbsent(server,key->new ArrayDeque<>()).add(() -> guarded(() -> {
            if (((ICancellableEvent)event).isCanceled() || get(event,"getPokemon")!=pokemon) return;
            Object storage=get(pokemon,"getStorage");
            if (storage==null || !(get(storage,"getOwner") instanceof ServerPlayerEntity owner)
                    || !owner.getUuid().equals(player.getUuid())) return;
            int dex=dex(pokemon);
            MissionsMod.event(player,Map.of("capture",1,"capture_species",1),"dex_"+dex,"capture:"+uuid(pokemon));
            if (ProfilesMod.adminTitles(server).firstCapture(player.getUuid(),dex))
                player.sendMessage(Text.literal("서버 최초 포획 칭호를 획득했습니다. 프로필 꾸미기에서 확인하세요."),false);
        }));
    }
    private static void battleEnded(Event event) throws Exception {
        if (Boolean.TRUE.equals(get(event,"isAbnormal")) || get(event,"getCause")!=type("api.battles.BattleEndCause").getField("NORMAL").get(null)) return;
        List<?> players=(List<?>)get(event,"getPlayers");
        if (players.size()!=1 || !(players.getFirst() instanceof ServerPlayerEntity player)) return;
        Object victory=type("api.battles.BattleResults").getField("VICTORY").get(null);
        Object result=getResult(event,player);
        if (!(result instanceof Optional<?> won) || won.orElse(null)!=victory) return;
        var opponents=new LinkedHashMap<UUID,Object>();
        for (Object side:((Map<?,?>)get(event,"getResults")).keySet()){
            if (get(side,"getEntity")==player) continue;
            if (!Boolean.TRUE.equals(get(side,"isWild"))) return;
            for (Object wrapper:(List<?>)get(side,"getTeamPokemon")){
                Object pokemon=get(wrapper,"getOriginalPokemon");
                if(!natural(pokemon))return;
                opponents.put(uuid(pokemon),pokemon);
            }
        }
        if (opponents.isEmpty()) return;
        UUID battle=BATTLES.computeIfAbsent(get(event,"getBattleController"),key->UUID.randomUUID());
        MissionsMod.event(player,Map.of("battle_win",1),null,"victory:"+battle);
        for(var opponent:opponents.entrySet()){
            int dex=dex(opponent.getValue());
            MissionsMod.event(player,Map.of("defeat",1,"defeat_species",1),"dex_"+dex,"defeat:"+opponent.getKey());
        }
    }
    private static Object getResult(Event e,ServerPlayerEntity player) throws ReflectiveOperationException {
        return e.getClass().getMethod("getResult",net.minecraft.entity.Entity.class).invoke(e,player);
    }
    private static void experience(Event event) throws Exception {
        Object storage=get(field(event,"pokemon"),"getStorage");
        int xp=(Integer)get(event,"getExperience");
        if (xp>0 && storage!=null && get(storage,"getOwner") instanceof ServerPlayerEntity player)
            MissionsMod.event(player,Map.of("xp",xp),null,null);
    }
    private static void leveled(Event event) throws Exception {
        int levels=(Integer)get(event,"getLevelChange");
        if(levels>0 && get(event,"getPlayer") instanceof ServerPlayerEntity player)
            MissionsMod.event(player,Map.of("level",levels),null,null);
    }
}
