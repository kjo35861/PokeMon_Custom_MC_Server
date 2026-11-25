package space.pocketmate.estates;

import com.google.gson.*;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.*;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.block.*;
import net.minecraft.component.DataComponentTypes;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.tag.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.stat.Stats;
import net.minecraft.util.*;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import org.slf4j.LoggerFactory;
import java.time.Clock;
import java.util.*;

public final class MissionsMod implements ModInitializer {
    private static final String CHANNEL="pocketmate:missions";
    private static final Map<MinecraftServer,MissionStore> STORES=new IdentityHashMap<>();
    private static final Map<UUID,Sample> SAMPLES=new HashMap<>();
    private static final Map<UUID,Long> SAMPLE_RETRY_AT=new HashMap<>();
    private record RequestStamp(String action,long time) {}
    private static final Map<UUID,RequestStamp> REQUESTS=new HashMap<>();
    private static final org.slf4j.Logger LOG=LoggerFactory.getLogger("pocketmate-missions");
    private record Sample(String date,Map<String,Integer> stats) {}
    private static boolean pokemonReady;
    public static boolean pokemonReady(){return pokemonReady;}
    public static void connectPokemon(){pokemonReady=true;}
    public static void event(ServerPlayerEntity player,Map<String,Integer> values,String species,String unique){
        if(player.isCreative()||player.isSpectator())return;
        MissionStore store=STORES.get(player.getServer());if(store==null)return;
        try{store.event(player.getUuid(),values,species,unique);}catch(Exception e){LOG.error("Mission progress save failed",e);}
    }
    private static String position(World world,BlockPos pos){return world.getRegistryKey().getValue()+":"+pos.asLong();}
    private static String mining(BlockState state){
        if(state.isIn(BlockTags.LOGS))return "logs";
        if(state.isIn(BlockTags.COAL_ORES)||state.isIn(BlockTags.IRON_ORES)||state.isIn(BlockTags.COPPER_ORES)||state.isIn(BlockTags.GOLD_ORES)||state.isIn(BlockTags.DIAMOND_ORES)||state.isIn(BlockTags.REDSTONE_ORES)||state.isIn(BlockTags.LAPIS_ORES)||state.isIn(BlockTags.EMERALD_ORES)||state.isOf(Blocks.NETHER_QUARTZ_ORE))return "ore";
        if(state.isOf(Blocks.SAND)||state.isOf(Blocks.RED_SAND))return "sand";
        if(state.isOf(Blocks.STONE)||state.isOf(Blocks.DEEPSLATE)||state.isOf(Blocks.GRANITE)||state.isOf(Blocks.DIORITE)||state.isOf(Blocks.ANDESITE))return "stone";
        return null;
    }
    public static void placed(World world,BlockPos pos,net.minecraft.entity.player.PlayerEntity player){
        if(!(player instanceof ServerPlayerEntity serverPlayer))return;
        MissionStore store=STORES.get(serverPlayer.getServer());if(store==null)return;
        BlockState state=world.getBlockState(pos);
        try{if(mining(state)!=null)store.placed(position(world,pos));}
        catch(Exception e){LOG.error("Placed-block mission guard save failed",e);return;}
        if(state.getBlock() instanceof CropBlock||state.isOf(Blocks.NETHER_WART)||state.isOf(Blocks.COCOA))event(serverPlayer,Map.of("plant",1),null,null);
    }
    public static void pistonMove(World world,List<BlockPos> blocks,net.minecraft.util.math.Direction direction){
        if(!(world instanceof net.minecraft.server.world.ServerWorld serverWorld))return;
        MissionStore store=STORES.get(serverWorld.getServer());if(store==null)return;
        Map<String,String> moves=new HashMap<>();for(BlockPos pos:blocks)moves.put(position(world,pos),position(world,pos.offset(direction)));
        try{store.movePlaced(moves);}catch(Exception e){LOG.error("Piston mission guard save failed",e);}
    }
    @Override public void onInitialize(){
        ServerLifecycleEvents.SERVER_STARTING.register(server->{
            try{STORES.put(server,new MissionStore(server.getSavePath(WorldSavePath.ROOT).resolve("data/pocketmate-missions.json"),Clock.systemUTC(),pokemonReady()));}
            catch(Exception e){LOG.error("Mission store unavailable; progress will not be reset",e);}
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(server->{STORES.remove(server);SAMPLES.clear();SAMPLE_RETRY_AT.clear();REQUESTS.clear();});
        ServerPlayConnectionEvents.JOIN.register((handler,sender,server)->assignAndBaseline(handler.player));
        ServerTickEvents.START_SERVER_TICK.register(server->{
            String date=MissionStore.dayAt(java.time.Instant.now()).toString();
            for(var player:server.getPlayerManager().getPlayerList()){
                Sample previous=SAMPLES.get(player.getUuid());if(previous==null||!previous.date.equals(date))assignAndBaseline(player);
            }
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler,server)->{SAMPLES.remove(handler.player.getUuid());SAMPLE_RETRY_AT.remove(handler.player.getUuid());REQUESTS.remove(handler.player.getUuid());});
        PlayerBlockBreakEvents.AFTER.register((world,player,pos,state,entity)->{
            if(!(player instanceof ServerPlayerEntity serverPlayer))return;
            MissionStore store=STORES.get(serverPlayer.getServer());if(store==null)return;
            try{boolean planted=store.removePlaced(position(world,pos));String metric=mining(state);
                if(metric!=null&&!planted)event(serverPlayer,Map.of(metric,1),null,null);
                if(state.getBlock() instanceof CropBlock crop&&crop.isMature(state))event(serverPlayer,Map.of("harvest",1),null,null);
            }catch(Exception e){LOG.error("Block mission update failed",e);}
        });
        ServerTickEvents.END_SERVER_TICK.register(server->{if(server.getTicks()%20==0)for(var player:server.getPlayerManager().getPlayerList())sampleSafely(player);});
        WebGuiBridge.listen(CHANNEL,(player,payload)->{if(player.getServer()!=null)player.getServer().execute(()->receive(player,payload));});
    }
    private static void assignAndBaseline(ServerPlayerEntity player){
        if(System.currentTimeMillis()<SAMPLE_RETRY_AT.getOrDefault(player.getUuid(),0L))return;
        MissionStore store=STORES.get(player.getServer());if(store==null)return;
        try{store.view(player.getUuid());SAMPLES.remove(player.getUuid());sampleSafely(player);}
        catch(Exception e){SAMPLE_RETRY_AT.put(player.getUuid(),System.currentTimeMillis()+30000);LOG.error("Daily mission assignment temporarily unavailable",e);}
    }
    private static boolean sampleSafely(ServerPlayerEntity player){
        if(System.currentTimeMillis()<SAMPLE_RETRY_AT.getOrDefault(player.getUuid(),0L))return false;
        try{sample(player);SAMPLE_RETRY_AT.remove(player.getUuid());return true;}
        catch(RuntimeException e){
            SAMPLES.remove(player.getUuid());SAMPLE_RETRY_AT.put(player.getUuid(),System.currentTimeMillis()+30000);
            LOG.error("Mission statistics temporarily unavailable; server tick will continue",e);return false;
        }
    }
    private static void sample(ServerPlayerEntity player){
        Map<String,Integer> now=new HashMap<>();int planks=0,food=0;
        for(Item item:Registries.ITEM){
            var stack=item.getDefaultStack();
            if(stack.isIn(ItemTags.PLANKS))planks+=player.getStatHandler().getStat(Stats.CRAFTED.getOrCreateStat(item));
            if(stack.contains(DataComponentTypes.FOOD))food+=player.getStatHandler().getStat(Stats.CRAFTED.getOrCreateStat(item));
        }
        now.put("planks",planks);now.put("food",food);now.put("fish",MissionStatistics.custom(player.getStatHandler(),Stats.FISH_CAUGHT));
        long walk=MissionStatistics.centimeters(player.getStatHandler(),MissionStatistics.walking());
        now.put("walk",(int)Math.min(Integer.MAX_VALUE,walk/100));
        long total=walk+MissionStatistics.centimeters(player.getStatHandler(),MissionStatistics.otherTravel());
        now.put("travel",(int)Math.min(Integer.MAX_VALUE,total/100));
        String date=MissionStore.dayAt(java.time.Instant.now()).toString();Sample previous=SAMPLES.put(player.getUuid(),new Sample(date,now));
        if(previous==null||!previous.date.equals(date)||player.isCreative()||player.isSpectator())return;
        Map<String,Integer> values=new HashMap<>();now.forEach((k,v)->{int delta=v-previous.stats.getOrDefault(k,v);if(delta>0)values.put(k,delta);});
        if(!values.isEmpty())event(player,values,null,null);
    }
    private static void receive(ServerPlayerEntity player,String payload){
        String requestId="";
        try{
            if(payload==null||payload.length()>2048)throw new IllegalArgumentException();
            JsonObject request=JsonParser.parseString(payload).getAsJsonObject();requestId=request.get("requestId").getAsString();
            if(!requestId.matches("[A-Za-z0-9_-]{1,64}"))throw new IllegalArgumentException();
            String action=request.get("action").getAsString();
            long now=System.currentTimeMillis();RequestStamp last=REQUESTS.get(player.getUuid());if(last!=null&&last.action.equals(action)&&now-last.time<200)throw new IllegalArgumentException("잠시 후 다시 시도해주세요.");REQUESTS.put(player.getUuid(),new RequestStamp(action,now));
            MissionStore store=STORES.get(player.getServer());if(store==null)throw new IllegalStateException("임무 저장소를 사용할 수 없습니다.");
            JsonObject response=new JsonObject();
            if(action.equals("claim")){
                if(ShopMod.missionsPaused())throw new IllegalArgumentException(ShopMod.maintenanceMessage("임무 보상 수령은 현재 점검 중입니다. 진행도는 계속 집계됩니다."));
                String id=request.get("taskId").getAsString(),date=request.get("date").getAsString();
                if(!store.view(player.getUuid()).date().equals(date))throw new IllegalArgumentException("새로운 하루의 임무가 시작되었습니다. 다시 확인해주세요.");
                if(!store.claim(player.getUuid(),id))throw new IllegalArgumentException("아직 완료하지 않았거나 이미 수령한 보상입니다.");
                response.addProperty("message","보상 수령을 기록했습니다. 보상 구성은 준비 중입니다.");
            }else if(action.equals("reroll")){
                String id=request.get("taskId").getAsString(),date=request.get("date").getAsString();
                if(!sampleSafely(player))throw new IllegalStateException("통계를 확인하지 못해 교체하지 않았습니다. 잠시 후 다시 시도해주세요."); // Flush old deltas and establish the replacement baseline.
                if(!store.reroll(player.getUuid(),date,id))throw new IllegalArgumentException("교체할 수 없습니다. 남은 횟수·완료 여부·임무 날짜를 확인해주세요.");
                // The pre-reroll sample is already the exact baseline: this runs serially on the server thread.
                response.addProperty("message","같은 슬롯의 새 임무로 교체했습니다. 새 임무는 지금부터 집계합니다.");
            }else if(!action.equals("view"))throw new IllegalArgumentException();
            response.addProperty("type","snapshot");response.addProperty("requestId",requestId);response.add("missions",new Gson().toJsonTree(store.view(player.getUuid())));
            response.addProperty("rewardsPaused",ShopMod.missionsPaused());response.addProperty("pokemonReady",pokemonReady());WebGuiBridge.emit(player,CHANNEL,response.toString());
        }catch(Exception e){JsonObject error=new JsonObject();error.addProperty("type","error");error.addProperty("requestId",requestId);error.addProperty("message",e instanceof java.io.IOException?"저장하지 못했습니다. 다시 확인해주세요.":e.getMessage()==null?"올바르지 않은 임무 요청입니다.":e.getMessage());WebGuiBridge.emit(player,CHANNEL,error.toString());}
    }
}
