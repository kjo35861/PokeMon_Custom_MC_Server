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
    private record RequestStamp(String action,long time) {}
    private static final Map<UUID,RequestStamp> REQUESTS=new HashMap<>();
    private static final org.slf4j.Logger LOG=LoggerFactory.getLogger("pocketmate-missions");
    private record Sample(String date,Map<String,Integer> stats) {}
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
    @Override public void onInitialize(){
        ServerLifecycleEvents.SERVER_STARTING.register(server->{
            try{STORES.put(server,new MissionStore(server.getSavePath(WorldSavePath.ROOT).resolve("data/pocketmate-missions.json"),Clock.systemUTC(),false));}
            catch(Exception e){LOG.error("Mission store unavailable; progress will not be reset",e);}
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(server->{STORES.remove(server);SAMPLES.clear();REQUESTS.clear();});
        ServerPlayConnectionEvents.DISCONNECT.register((handler,server)->{SAMPLES.remove(handler.player.getUuid());REQUESTS.remove(handler.player.getUuid());});
        PlayerBlockBreakEvents.AFTER.register((world,player,pos,state,entity)->{
            if(!(player instanceof ServerPlayerEntity serverPlayer))return;
            MissionStore store=STORES.get(serverPlayer.getServer());if(store==null)return;
            try{boolean planted=store.removePlaced(position(world,pos));String metric=mining(state);
                if(metric!=null&&!planted)event(serverPlayer,Map.of(metric,1),null,null);
                if(state.getBlock() instanceof CropBlock crop&&crop.isMature(state))event(serverPlayer,Map.of("harvest",1),null,null);
            }catch(Exception e){LOG.error("Block mission update failed",e);}
        });
        ServerTickEvents.END_SERVER_TICK.register(server->{if(server.getTicks()%20==0)for(var player:server.getPlayerManager().getPlayerList())sample(player);});
        WebGuiBridge.listen(CHANNEL,(player,payload)->{if(player.getServer()!=null)player.getServer().execute(()->receive(player,payload));});
    }
    private static int custom(ServerPlayerEntity player,String name){return player.getStatHandler().getStat(Stats.CUSTOM.getOrCreateStat(Identifier.ofVanilla(name)));}
    private static void sample(ServerPlayerEntity player){
        Map<String,Integer> now=new HashMap<>();int planks=0,food=0;
        for(Item item:Registries.ITEM){
            var stack=item.getDefaultStack();
            if(stack.isIn(ItemTags.PLANKS))planks+=player.getStatHandler().getStat(Stats.CRAFTED.getOrCreateStat(item));
            if(stack.contains(DataComponentTypes.FOOD))food+=player.getStatHandler().getStat(Stats.CRAFTED.getOrCreateStat(item));
        }
        now.put("planks",planks);now.put("food",food);now.put("fish",custom(player,"fish_caught"));
        long walk=(long)custom(player,"walk_one_cm")+custom(player,"sprint_one_cm")+custom(player,"crouch_one_cm");
        now.put("walk",(int)Math.min(Integer.MAX_VALUE,walk/100));
        long total=walk;for(String stat:List.of("swim_one_cm","walk_on_water_one_cm","walk_under_water_one_cm","boat_one_cm","horse_one_cm","pig_one_cm","strider_one_cm"))total+=custom(player,stat);
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
                String id=request.get("taskId").getAsString(),date=request.get("date").getAsString();
                if(!store.view(player.getUuid()).date().equals(date))throw new IllegalArgumentException("새로운 하루의 임무가 시작되었습니다. 다시 확인해주세요.");
                if(!store.claim(player.getUuid(),id))throw new IllegalArgumentException("아직 완료하지 않았거나 이미 수령한 보상입니다.");
                response.addProperty("message","보상 수령을 기록했습니다. 보상 구성은 준비 중입니다.");
            }else if(!action.equals("view"))throw new IllegalArgumentException();
            response.addProperty("type","snapshot");response.addProperty("requestId",requestId);response.add("missions",new Gson().toJsonTree(store.view(player.getUuid())));
            response.addProperty("pokemonReady",false);WebGuiBridge.emit(player,CHANNEL,response.toString());
        }catch(Exception e){JsonObject error=new JsonObject();error.addProperty("type","error");error.addProperty("requestId",requestId);error.addProperty("message",e instanceof java.io.IOException?"저장하지 못했습니다. 다시 확인해주세요.":e.getMessage()==null?"올바르지 않은 임무 요청입니다.":e.getMessage());WebGuiBridge.emit(player,CHANNEL,error.toString());}
    }
}
