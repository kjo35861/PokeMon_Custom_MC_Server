package space.pocketmate.estates;

import com.google.gson.*;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.command.argument.EntityArgumentType;
import com.mojang.brigadier.arguments.LongArgumentType;
import net.minecraft.text.Text;
import static net.minecraft.server.command.CommandManager.*;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.util.math.Box;
import net.minecraft.util.math.Direction;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.WorldSavePath;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkPos;
import net.minecraft.world.Heightmap;
import net.minecraft.world.World;
import net.minecraft.world.chunk.WorldChunk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

public final class EstatesMod implements ModInitializer {
    private static final Logger LOG=LoggerFactory.getLogger("pocketmate-estates");
    private static final Gson GSON=new Gson();
    private static final String CHANNEL="pocketmate:estate";
    private static final int RADIUS=8;
    private static final class Config { boolean freeTestMode=true; }
    private static final class Session {
        ClaimStore store;
        String failure;
        boolean freeTestMode;
        final Map<UUID,Long> views=new HashMap<>(),purchases=new HashMap<>(),travels=new HashMap<>();
        final Map<UUID,LinkedHashSet<String>> mutations=new HashMap<>();
        final Map<UUID,Integer> radii=new HashMap<>();
        final Map<UUID,String> mapSessions=new HashMap<>();
    }
    private static final Map<MinecraftServer,Session> sessions=new IdentityHashMap<>();
    @Override public void onInitialize() {
        ServerLifecycleEvents.SERVER_STARTING.register(this::start);
        ServerLifecycleEvents.SERVER_STOPPED.register(server->sessions.remove(server));
        ServerPlayConnectionEvents.JOIN.register((handler,sender,server)->seen(server,handler.player));
        ServerPlayConnectionEvents.DISCONNECT.register((handler,server)->{
            seen(server,handler.player);Session state=sessions.get(server);if(state!=null){UUID id=handler.player.getUuid();state.views.remove(id);state.purchases.remove(id);state.travels.remove(id);state.mutations.remove(id);state.radii.remove(id);state.mapSessions.remove(id);}
        });
        WebGuiBridge.listen(CHANNEL,(player,payload)->{
            MinecraftServer server=player.getServer();
            if(server!=null)server.execute(()->receive(server,player,payload));
        });
        CommandRegistrationCallback.EVENT.register((dispatcher,access,environment)->dispatcher.register(literal("pmestate").requires(source->source.hasPermissionLevel(2))
            .then(literal("testcredit").then(argument("player",EntityArgumentType.player()).then(argument("amount",LongArgumentType.longArg(1,EstateRules.MAX_MONEY)).executes(context->{
                Session state=sessions.get(context.getSource().getServer());
                try{
                    if(state==null||state.store==null||state.failure!=null||!state.freeTestMode)throw new IllegalStateException();
                    ServerPlayerEntity target=EntityArgumentType.getPlayer(context,"player");state.store.creditWallet(target.getUuid(),LongArgumentType.getLong(context,"amount"));
                    context.getSource().sendFeedback(()->Text.literal("테스트 지갑에 재화를 지급했습니다. 금고 탭에서 확인하세요."),false);return 1;
                }catch(Exception failure){context.getSource().sendError(Text.literal("테스트 지급을 처리하지 못했습니다. freeTestMode 설정과 저장 상태를 확인해주세요."));return 0;}
            }))))));
        LOG.info("Pocketmate estates registered: server-authoritative Overworld ownership");
    }
    private void start(MinecraftServer server) {
        Session state=new Session();sessions.put(server,state);
        try {
            Path configPath=FabricLoader.getInstance().getConfigDir().resolve("pocketmate-estates.json");
            Config config;
            if(Files.exists(configPath))config=GSON.fromJson(Files.readString(configPath),Config.class);
            else{config=new Config();Files.createDirectories(configPath.getParent());Files.writeString(configPath,GSON.toJson(config),StandardOpenOption.CREATE_NEW);}
            if(config==null)throw new IOException("Invalid estates configuration");
            state.freeTestMode=config.freeTestMode;
            state.store=new ClaimStore(server.getSavePath(WorldSavePath.ROOT).resolve("data/pocketmate-estates.json"));
        } catch(Exception error){state.failure="영지 저장 파일 또는 설정을 읽지 못했습니다. 소유권 보호를 위해 구매를 중단했습니다.";LOG.error("Estate store unavailable; ownership is not reset",error);}
    }
    static ClaimStore shopWallet(MinecraftServer server){
        Session state=sessions.get(server);
        if(state==null||state.failure!=null||state.store==null)throw new IllegalStateException("개인 재화 저장소를 사용할 수 없습니다.");
        return state.store;
    }
    private void seen(MinecraftServer server,ServerPlayerEntity player){
        Session state=sessions.get(server);if(state==null||state.store==null)return;
        try{state.store.seen(player.getUuid(),NicknamesMod.name(player),System.currentTimeMillis());}
        catch(IOException error){LOG.error("Could not persist player last-seen",error);state.failure="영지 정보를 저장하지 못했습니다. 관리자에게 문의해주세요.";}
    }
    private static UUID uuid(JsonObject request,String field){return UUID.fromString(request.get(field).getAsString());}
    private static String text(JsonObject request,String field,int limit){JsonElement value=request.get(field);if(value==null||!value.isJsonPrimitive()||!value.getAsJsonPrimitive().isString())throw new IllegalArgumentException();String text=value.getAsString();if(text.length()>limit)throw new IllegalArgumentException();return text;}
    private static int integer(JsonObject request,String key) {
        JsonElement value=request.get(key);
        if(value==null||!value.isJsonPrimitive()||!value.getAsJsonPrimitive().isNumber())throw new IllegalArgumentException();
        double number=value.getAsDouble();if(!Double.isFinite(number)||number!=Math.rint(number)||number<Integer.MIN_VALUE||number>Integer.MAX_VALUE)throw new IllegalArgumentException();
        return (int)number;
    }
    private static long money(JsonObject request,String key){JsonElement value=request.get(key);if(value==null||!value.isJsonPrimitive()||!value.getAsJsonPrimitive().isNumber())throw new IllegalArgumentException();try{long amount=value.getAsBigDecimal().toBigIntegerExact().longValueExact();if(amount<0||amount>EstateRules.MAX_MONEY)throw new IllegalArgumentException();return amount;}catch(ArithmeticException invalid){throw new IllegalArgumentException(invalid);}}
    private void receive(MinecraftServer server,ServerPlayerEntity player,String payload) {
        String requestId="";
        try {
            if(payload==null||payload.length()>24576)throw new IllegalArgumentException();
            JsonObject request=JsonParser.parseString(payload).getAsJsonObject();
            requestId=request.has("requestId")?request.get("requestId").getAsString():"";
            if(!requestId.matches("[A-Za-z0-9_-]{1,64}"))throw new IllegalArgumentException();
            String action=request.get("action").getAsString();
            Session state=sessions.get(server);
            if(state==null||state.failure!=null||state.store==null){error(player,requestId,state==null?"영지 서버를 준비 중입니다.":state.failure);return;}
            UUID id=player.getUuid();long now=System.currentTimeMillis();
            if(action.equals("view")) {
                Long last=state.views.get(id);
                if(last!=null&&now-last<250){error(player,requestId,"지도를 너무 빠르게 요청했습니다. 잠시 후 다시 시도해주세요.");return;}
                state.views.put(id,now);
                ChunkPos current=player.getChunkPos();
                ClaimStore.Estate estate=state.store.estateFor(id);List<ClaimStore.Claim> owned=state.store.owned(estate==null?id:estate.owner());
                int cx=owned.isEmpty()?current.x:owned.getFirst().x(),cz=owned.isEmpty()?current.z:owned.getFirst().z();
                if(request.has("centerX")){cx=integer(request,"centerX");cz=integer(request,"centerZ");}
                if(!ClaimStore.inBounds(cx,cz))throw new IllegalArgumentException();
                int radius=request.has("radius")?integer(request,"radius"):RADIUS;
                if(radius<2||radius>48)throw new IllegalArgumentException();
                state.radii.put(id,radius);
                if(request.has("mapSession")){String token=text(request,"mapSession",64);if(!token.matches("[A-Za-z0-9_-]{1,64}"))throw new IllegalArgumentException();state.mapSessions.put(id,token);}
                snapshot(server,player,state,requestId,cx,cz,null);return;
            }
            if(action.equals("players")) {players(server,player,state,requestId,request.has("query")?text(request,"query",32):"");return;}
            if(!action.equals("players")){
                LinkedHashSet<String> seen=state.mutations.computeIfAbsent(id,key->new LinkedHashSet<>());
                if(!seen.add(requestId)){error(player,requestId,"이미 처리한 요청입니다. 새로고침 후 확인해주세요.");return;}
                if(seen.size()>128)seen.remove(seen.iterator().next());
            }
            if(action.equals("teleportHome")){
                Long last=state.travels.get(id);if(last!=null&&now-last<5000){error(player,requestId,"마을 이동 후 5초 뒤에 다시 이용해 주세요.");return;}
                try{
                    ClaimStore.Home home=state.store.homeFor(id);
                    if(!player.isAlive()||player.isSleeping()||player.hasVehicle())throw new ClaimStore.Denied("지금은 마을로 이동할 수 없습니다. 깨어 있는 상태에서 탈것에서 내려 다시 시도해 주세요.");
                    ServerWorld overworld=server.getOverworld();ClaimStore.Home target=resolveHome(overworld,player,home);
                    if(target==null)throw new ClaimStore.Denied("홈 지점이 막혀 있거나 안전하지 않습니다. 영주에게 홈 지점을 다시 지정해 달라고 요청해 주세요.");
                    player.teleport(overworld,target.x(),target.y(),target.z(),target.yaw(),target.pitch());player.fallDistance=0;
                    state.travels.put(id,now);
                    JsonObject response=new JsonObject();response.addProperty("type","travel");response.addProperty("requestId",requestId);response.addProperty("message","영지 홈으로 이동했습니다.");WebGuiBridge.emit(player,CHANNEL,GSON.toJson(response));
                }catch(ClaimStore.Denied denied){error(player,requestId,denied.getMessage());}
                return;
            }
            if(action.equals("setHome")){
                Long last=state.purchases.get(id);if(last!=null&&now-last<450){error(player,requestId,"요청을 처리 중입니다. 잠시 후 다시 시도해 주세요.");return;}state.purchases.put(id,now);
                try{
                    if(!player.getWorld().getRegistryKey().equals(World.OVERWORLD))throw new ClaimStore.Denied("홈 지점은 오버월드의 내 영지 안에서만 지정할 수 있습니다.");
                    ClaimStore.Home home=standingHome(player);
                    if(!player.isAlive()||player.hasVehicle()||!player.isOnGround()||!safeHome(server.getOverworld(),player,home))throw new ClaimStore.Denied("안전하고 단단한 바닥에 서서 홈 지점을 지정해 주세요.");
                    state.store.setHome(id,home);
                    snapshot(server,player,state,requestId,(int)Math.floor(home.x()/16),(int)Math.floor(home.z()/16),"현재 위치를 영지 홈으로 지정했습니다.");
                }catch(ClaimStore.Denied denied){error(player,requestId,denied.getMessage());}
                catch(IOException failure){LOG.error("Estate home not committed",failure);error(player,requestId,"홈 지점을 저장하지 못했습니다. 기존 홈 지점은 유지됩니다.");}
                return;
            }
            if(Set.of("upgrade","deposit","invite","acceptInvite","declineInvite","role","kick","notice","image","deleteEstate").contains(action)){
                Long last=state.purchases.get(id);if(last!=null&&now-last<450){error(player,requestId,"요청을 처리 중입니다. 잠시 후 다시 시도해주세요.");return;}state.purchases.put(id,now);
                try{
                    switch(action){
                        case "upgrade"->state.store.upgrade(id,integer(request,"expectedLevel"));
                        case "deposit"->state.store.deposit(id,money(request,"amount"));
                        case "invite"->state.store.invite(id,uuid(request,"target"));
                        case "acceptInvite"->state.store.answerInvite(id,uuid(request,"estate"),true);
                        case "declineInvite"->state.store.answerInvite(id,uuid(request,"estate"),false);
                        case "role"->state.store.changeRole(id,uuid(request,"target"),ClaimStore.Role.valueOf(text(request,"role",16)));
                        case "kick"->state.store.kick(id,uuid(request,"target"));
                        case "notice"->state.store.updateNotice(id,text(request,"text",1000));
                        case "image"->state.store.updateImage(id,text(request,"image",18000));
                        case "deleteEstate"->state.store.deleteEstate(id,text(request,"name",80));
                    }
                    ClaimStore.Estate estate=state.store.estateFor(id);List<ClaimStore.Claim> owned=state.store.owned(estate==null?id:estate.owner());ChunkPos current=player.getChunkPos();
                    String message=switch(action){case "upgrade"->"영지 레벨을 올렸습니다. 구매 가능한 최대 청크 수가 증가했습니다.";case "deposit"->"개인 재화를 영지 금고에 저축했습니다.";case "invite"->"초대를 보냈습니다. 상대방이 수락하면 마을원이 됩니다.";case "acceptInvite"->"영지에 가입했습니다.";case "declineInvite"->"초대를 거절했습니다.";case "role"->"마을원 등급을 변경했습니다.";case "kick"->"마을원을 추방했습니다.";case "notice"->"영주 공지를 저장했습니다.";case "image"->"대표 이미지를 저장했습니다.";default->"영지를 삭제했습니다. 모든 청크가 무주 상태로 돌아갔습니다.";};
                    snapshot(server,player,state,requestId,owned.isEmpty()?current.x:owned.getFirst().x(),owned.isEmpty()?current.z:owned.getFirst().z(),message);
                }catch(ClaimStore.Denied denied){error(player,requestId,denied.getMessage());}
                catch(IOException failed){LOG.error("Estate management not committed",failed);error(player,requestId,"저장에 실패하여 변경을 취소했습니다. 다시 확인해주세요.");}
                return;
            }
            if(!action.equals("create")&&!action.equals("buy"))throw new IllegalArgumentException();
            Long last=state.purchases.get(id);
            if(last!=null&&now-last<450){error(player,requestId,"구매 요청을 처리 중입니다. 잠시 후 다시 시도해주세요.");return;}
            state.purchases.put(id,now);
            if(!player.getWorld().getRegistryKey().equals(World.OVERWORLD)){error(player,requestId,"영지는 오버월드에서만 생성하거나 구매할 수 있습니다.");return;}
            List<ClaimStore.Key> selection=new ArrayList<>();
            if(action.equals("buy")&&request.has("chunks")){
                JsonArray chunks=request.getAsJsonArray("chunks");
                if(chunks.isEmpty()||chunks.size()>128)throw new IllegalArgumentException();
                for(JsonElement entry:chunks){JsonObject chunk=entry.getAsJsonObject();selection.add(new ClaimStore.Key(integer(chunk,"x"),integer(chunk,"z")));}
            }else selection.add(new ClaimStore.Key(integer(request,"x"),integer(request,"z")));
            int x=selection.getFirst().x(),z=selection.getFirst().z();
            if(!ClaimStore.inBounds(x,z))throw new IllegalArgumentException();
            if(action.equals("create")) {
                ChunkPos current=player.getChunkPos();
                if(x!=current.x||z!=current.z){error(player,requestId,"서 있는 청크가 바뀌었습니다. 현재 위치를 다시 확인하고 생성해주세요.");return;}
                x=current.x;z=current.z;
            }
            for(ClaimStore.Key chunk:selection)if(!ClaimStore.inBounds(chunk.x(),chunk.z())||!server.getOverworld().getWorldBorder().contains(new ChunkPos(chunk.x(),chunk.z()))){error(player,requestId,"월드 경계 밖의 청크는 구매할 수 없습니다.");return;}
            try {
                if(action.equals("create"))state.store.createEstate(id,NicknamesMod.name(player),text(request,"name",80),x,z,standingHome(player));
                else {
                    ClaimStore.Progress progress=state.store.progress(id);
                    if(progress==null){error(player,requestId,"영주만 청크를 구매할 수 있습니다.");return;}
                    if(integer(request,"expectedPurchasedChunks")!=progress.purchasedChunks()||money(request,"expectedTotal")!=EstateRules.purchasePrice(progress.purchasedChunks(),selection.size())){error(player,requestId,"청크 가격이 변경되었습니다. 새로고침 후 구매 금액을 다시 확인해주세요.");return;}
                    state.store.buyBatch(id,NicknamesMod.name(player),selection);
                }
                LOG.info("Estate claims persisted: player={} count={} mode=estate-wallet",id,selection.size());
                snapshot(server,player,state,requestId,x,z,action.equals("create")?"기본 1청크로 레벨 0 영지를 생성했습니다.":selection.size()+"개 청크 구매가 완료되었습니다.");
            } catch(ClaimStore.Rejected rejection){error(player,requestId,switch(rejection.reason){
                case OCCUPIED->"이미 소유주가 있는 청크입니다. 중복 구매하거나 소유권을 가져올 수 없습니다.";
                case ALREADY_HAS_ESTATE->"이미 영지가 있습니다. 영지관리에서 인접 청크를 구매해주세요.";
                case NO_ESTATE->"먼저 현재 위치에서 영지를 생성해주세요.";
                case NOT_ADJACENT->"내 영지와 한 면 이상 이어지지 않은 청크가 있습니다. 선택한 청크가 서로 연결되어 기존 영지에 닿도록 선택해주세요. 대각선은 연결로 인정되지 않습니다. 전체 구매가 취소되었습니다.";
                case OUT_OF_BOUNDS->"구매 가능한 좌표 범위를 벗어났습니다.";
                case CHUNK_LIMIT->"현재 영지 레벨의 청크 한도를 초과합니다. 금고에서 레벨을 올린 뒤 확장해주세요. 전체 구매가 취소되었습니다.";
                case INVALID_SELECTION->"구매할 청크를 중복 없이 1~128개 선택해주세요.";
            });}
            catch(ClaimStore.Denied denied){error(player,requestId,denied.getMessage());}
            catch(IOException saveError){LOG.error("Estate purchase not committed",saveError);error(player,requestId,"영지 정보를 저장하지 못해 구매를 취소했습니다. 소유권은 변경되지 않았습니다.");}
        } catch(Exception malformed){LOG.debug("Rejected malformed estate request",malformed);error(player,requestId,"잘못된 영지 요청입니다. 메뉴에서 다시 시도해주세요.");}
    }
    private static ClaimStore.Home standingHome(ServerPlayerEntity player){return new ClaimStore.Home(player.getX(),player.getY(),player.getZ(),player.getYaw(),player.getPitch(),false);}
    private static boolean dangerous(BlockState state){return state.isOf(Blocks.MAGMA_BLOCK)||state.isOf(Blocks.CACTUS)||state.isOf(Blocks.CAMPFIRE)||state.isOf(Blocks.SOUL_CAMPFIRE)||state.isOf(Blocks.FIRE)||state.isOf(Blocks.SOUL_FIRE)||state.isOf(Blocks.SWEET_BERRY_BUSH)||state.isOf(Blocks.WITHER_ROSE)||state.isOf(Blocks.POWDER_SNOW)||state.isOf(Blocks.NETHER_PORTAL)||state.isOf(Blocks.END_PORTAL)||state.isOf(Blocks.END_GATEWAY);}
    private static boolean safeHome(ServerWorld world,ServerPlayerEntity player,ClaimStore.Home home){
        BlockPos feet=BlockPos.ofFloored(home.x(),home.y(),home.z()),ground=BlockPos.ofFloored(home.x(),home.y()-.01,home.z());
        if(!world.getWorldBorder().contains(feet)||home.y()<world.getBottomY()+1||home.y()+1.8>=world.getTopY())return false;
        for(BlockPos pos:List.of(ground,feet,feet.up())){BlockState state=world.getBlockState(pos);if(dangerous(state)||!state.getFluidState().isEmpty())return false;}
        return world.getBlockState(ground).isSideSolidFullSquare(world,ground,Direction.UP)&&world.isSpaceEmpty(player,new Box(home.x()-.3,home.y(),home.z()-.3,home.x()+.3,home.y()+1.8,home.z()+.3));
    }
    private static ClaimStore.Home resolveHome(ServerWorld world,ServerPlayerEntity player,ClaimStore.Home home){
        int chunkX=(int)Math.floor(home.x()/16),chunkZ=(int)Math.floor(home.z()/16);
        if(!world.getWorldBorder().contains(new ChunkPos(chunkX,chunkZ)))return null;
        world.getChunk(chunkX,chunkZ); // Only load the registered Overworld home chunk.
        if(!home.surface())return safeHome(world,player,home)?home:null;
        // Old stores never recorded a Y coordinate. Search the first owned chunk's surface only.
        for(int dz=0;dz<16;dz++)for(int dx=0;dx<16;dx++){
            int x=chunkX*16+(8+dx)%16,z=chunkZ*16+(8+dz)%16;
            ClaimStore.Home target=new ClaimStore.Home(x+.5,world.getTopY(Heightmap.Type.MOTION_BLOCKING_NO_LEAVES,x,z),z+.5,home.yaw(),home.pitch(),false);
            if(safeHome(world,player,target))return target;
        }
        return null;
    }
    private void snapshot(MinecraftServer server,ServerPlayerEntity player,Session state,String requestId,int cx,int cz,String message) {
        UUID id=player.getUuid();ChunkPos standing=player.getChunkPos();ClaimStore.Estate estate=state.store.estateFor(id);UUID estateId=estate==null?id:estate.owner();List<ClaimStore.Claim> mine=state.store.owned(estateId);
        JsonObject data=new JsonObject();data.addProperty("type","snapshot");data.addProperty("requestId",requestId);data.addProperty("dimension","minecraft:overworld");data.addProperty("mapSession",state.mapSessions.getOrDefault(id,requestId));
        data.addProperty("playerId",id.toString());data.add("appearance",ProfilesMod.publicAppearance(server,id));
        data.addProperty("estateName",estate==null?"":estate.name());data.addProperty("isLord",estate!=null&&estate.owner().equals(id));data.addProperty("hasEstate",estate!=null);
        data.addProperty("freeTestMode",false);data.addProperty("testEconomy",state.freeTestMode);data.addProperty("purchaseEnabled",estate==null||estate.owner().equals(id));data.addProperty("ownedCount",mine.size());
        data.addProperty("inOverworld",player.getWorld().getRegistryKey().equals(World.OVERWORLD));data.addProperty("currentX",standing.x);data.addProperty("currentZ",standing.z);
        ClaimStore.Claim current=state.store.get(standing.x,standing.z);data.addProperty("currentOwner",current==null?"":current.ownerName());
        ClaimStore.Progress progress=estate==null?null:state.store.progress(estate.owner());
        data.addProperty("memberLimit",EstateRules.memberLimit(progress==null?0:progress.level()));data.addProperty("estateLevel",progress==null?0:progress.level());data.addProperty("chunkLimit",EstateRules.limit(progress==null?0:progress.level()));data.addProperty("treasury",progress==null?0:progress.treasury());
        data.addProperty("purchasedChunks",progress==null?1:progress.purchasedChunks());data.addProperty("personalBalance",state.store.wallet(id));
        data.addProperty("lordBalance",estate!=null&&estate.owner().equals(id)?state.store.wallet(id):0);
        data.addProperty("nextChunkPrice",EstateRules.nextChunkPrice(progress==null?1:progress.purchasedChunks()));
        JsonObject pricing=new JsonObject();pricing.addProperty("freeChunks",4);pricing.addProperty("base",20000);pricing.addProperty("increment",2500);data.add("pricing",pricing);
        JsonArray levels=new JsonArray();for(int level=0;level<=EstateRules.MAX_LEVEL;level++){JsonObject row=new JsonObject();row.addProperty("level",level);row.addProperty("cost",EstateRules.cost(level));row.addProperty("limit",EstateRules.limit(level));row.addProperty("memberLimit",EstateRules.memberLimit(level));levels.add(row);}data.add("levels",levels);
        JsonArray ledger=new JsonArray();if(progress!=null)for(var entry:progress.ledger()){JsonObject row=new JsonObject();row.addProperty("type",entry.type());row.addProperty("amount",entry.amount());row.addProperty("level",entry.level());row.addProperty("at",entry.at());ledger.add(row);}data.add("vaultHistory",ledger);
        data.addProperty("currentMine",current!=null&&current.owner().equals(estateId));data.addProperty("centerX",cx);data.addProperty("centerZ",cz);data.addProperty("radius",state.radii.getOrDefault(id,RADIUS));
        int radius=state.radii.getOrDefault(id,RADIUS);data.addProperty("playerName",NicknamesMod.name(player));
        if(estate!=null){ClaimStore.Home home=estate.home();data.add("home",GSON.toJsonTree(home));data.addProperty("homeX",(int)Math.floor(home.x()/16));data.addProperty("homeZ",(int)Math.floor(home.z()/16));}
        ClaimStore.Claim standingClaim=player.getWorld().getRegistryKey().equals(World.OVERWORLD)?state.store.get(standing.x,standing.z):null;
        data.addProperty("canSetHome",estate!=null&&estate.owner().equals(id)&&standingClaim!=null&&standingClaim.owner().equals(id));
        if(message!=null)data.addProperty("message",message);
        JsonArray cells=new JsonArray();ServerWorld world=server.getOverworld();
        for(int z=cz-radius;z<=cz+radius;z++)for(int x=cx-radius;x<=cx+radius;x++) {
            JsonObject cell=new JsonObject();cell.addProperty("x",x);cell.addProperty("z",z);
            ClaimStore.Claim claim=state.store.get(x,z);cell.addProperty("owner",claim==null?"":claim.ownerName());cell.addProperty("mine",claim!=null&&claim.owner().equals(estateId));
            cell.addProperty("adjacent",claim==null&&state.store.adjacent(estateId,x,z));
            cells.add(cell);
        }
        // Keep each WebGUI event below its 32768-character payload limit even at maximum zoom-out.
        int batch=160;
        JsonArray first=new JsonArray();for(int i=0;i<Math.min(batch,cells.size());i++)first.add(cells.get(i));
        data.add("cells",first);data.addProperty("totalCells",cells.size());
        WebGuiBridge.emit(player,"pocketmate:estate",GSON.toJson(data));
        community(server,player,state,requestId,estate);
        for(int offset=batch;offset<cells.size();offset+=batch){
            JsonObject page=new JsonObject();page.addProperty("type","cells");page.addProperty("requestId",requestId);
            JsonArray subset=new JsonArray();for(int i=offset;i<Math.min(offset+batch,cells.size());i++)subset.add(cells.get(i));
            page.add("cells",subset);WebGuiBridge.emit(player,"pocketmate:estate",GSON.toJson(page));
        }
    }
    private void community(MinecraftServer server,ServerPlayerEntity player,Session state,String requestId,ClaimStore.Estate estate){
        JsonObject data=new JsonObject();data.addProperty("type","community");data.addProperty("requestId",requestId);
        data.addProperty("announcement",estate==null?"":estate.announcement());JsonArray members=new JsonArray(),outgoing=new JsonArray(),incoming=new JsonArray();
        if(estate!=null){
            for(ClaimStore.Member member:estate.members()){
                ClaimStore.KnownPlayer known=state.store.known(member.id());ServerPlayerEntity online=server.getPlayerManager().getPlayer(member.id());
                JsonObject item=new JsonObject();item.addProperty("id",member.id().toString());item.addProperty("name",online!=null?NicknamesMod.name(online):NicknamesMod.name(server,member.id(),known!=null?known.name():member.name()));item.addProperty("role",member.role().name());item.addProperty("online",online!=null);item.addProperty("lastSeen",online!=null?System.currentTimeMillis():known==null?member.joinedAt():known.lastSeen());item.add("appearance",ProfilesMod.publicAppearance(server,member.id()));members.add(item);
            }
            if(estate.owner().equals(player.getUuid()))for(ClaimStore.Invitation invite:estate.invitations()){if(invite.at()<System.currentTimeMillis()-7*86400000L)continue;JsonObject item=new JsonObject();item.addProperty("id",invite.id().toString());item.addProperty("name",NicknamesMod.name(server,invite.id(),invite.name()));item.addProperty("at",invite.at());item.add("appearance",ProfilesMod.publicAppearance(server,invite.id()));outgoing.add(item);}
        }
        for(ClaimStore.Estate invitation:state.store.invitationsFor(player.getUuid())){JsonObject item=new JsonObject();item.addProperty("id",invitation.owner().toString());item.addProperty("name",invitation.name());incoming.add(item);}
        data.add("members",members);data.add("outgoingInvites",outgoing);data.add("incomingInvites",incoming);WebGuiBridge.emit(player,CHANNEL,GSON.toJson(data));
        JsonObject image=new JsonObject();image.addProperty("type","image");image.addProperty("requestId",requestId);image.addProperty("image",estate==null?"":estate.image());WebGuiBridge.emit(player,CHANNEL,GSON.toJson(image));
    }
    private void players(MinecraftServer server,ServerPlayerEntity player,Session state,String requestId,String query){
        ClaimStore.Estate estate=state.store.estateFor(player.getUuid());
        if(estate==null||!estate.owner().equals(player.getUuid())){error(player,requestId,"유저 초대는 영주만 할 수 있습니다.");return;}
        JsonObject response=new JsonObject();response.addProperty("type","players");response.addProperty("requestId",requestId);JsonArray result=new JsonArray();
        String search=query.toLowerCase(Locale.ROOT);
        state.store.knownPlayers().stream().filter(p->(p.name().toLowerCase(Locale.ROOT).contains(search)||NicknamesMod.name(server,p.id(),p.name()).toLowerCase(Locale.ROOT).contains(search))).sorted(Comparator.comparing((ClaimStore.KnownPlayer p)->server.getPlayerManager().getPlayer(p.id())==null).thenComparing(ClaimStore.KnownPlayer::name)).filter(p->!search.isBlank()||server.getPlayerManager().getPlayer(p.id())!=null).limit(60).forEach(p->{
            JsonObject item=new JsonObject();item.addProperty("id",p.id().toString());item.addProperty("name",NicknamesMod.name(server,p.id(),p.name()));item.addProperty("online",server.getPlayerManager().getPlayer(p.id())!=null);
            item.add("appearance",ProfilesMod.publicAppearance(server,p.id()));
            boolean invited=estate.invitations().stream().anyMatch(i->i.id().equals(p.id())&&i.at()>=System.currentTimeMillis()-7*86400000L);item.addProperty("available",state.store.estateFor(p.id())==null&&!invited);item.addProperty("status",invited?"초대 대기":state.store.estateFor(p.id())!=null?"영지 소속":"초대 가능");result.add(item);
        });response.add("players",result);WebGuiBridge.emit(player,CHANNEL,GSON.toJson(response));
    }
    private void error(ServerPlayerEntity player,String requestId,String message) {
        JsonObject data=new JsonObject();data.addProperty("type","error");data.addProperty("requestId",requestId);data.addProperty("message",message==null?"영지 서버를 사용할 수 없습니다.":message);
        WebGuiBridge.emit(player,"pocketmate:estate",GSON.toJson(data));
    }
}
