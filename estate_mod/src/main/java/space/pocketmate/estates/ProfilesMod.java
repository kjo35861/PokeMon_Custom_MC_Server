package space.pocketmate.estates;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.command.argument.EntityArgumentType;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.minecraft.util.WorldSavePath;
import java.util.*;
import org.slf4j.LoggerFactory;
import static net.minecraft.server.command.CommandManager.*;

public final class ProfilesMod implements ModInitializer {
    private static final Map<MinecraftServer,ProfileStore> stores=new IdentityHashMap<>();
    private final Map<UUID,Long> requests=new HashMap<>();
    private static final String CHANNEL="pocketmate:profile";
    public static JsonObject publicAppearance(MinecraftServer server,UUID id){
        ProfileStore store=stores.get(server);
        return store==null?new JsonObject():new Gson().toJsonTree(store.appearance(id)).getAsJsonObject();
    }
    public static Text titledName(ServerPlayerEntity player,Text original){
        ProfileStore store=stores.get(player.getServer());
        if(store==null)return original;
        String title=store.equippedTitle(player.getUuid());
        if(title.equals("none"))return original;
        var item=store.cosmetic("title",title);
        if(item==null)return original;
        int color=Integer.parseInt(item.color().substring(1),16);
        var prefix=Text.empty();
        if(!item.glyph().isEmpty()){
            prefix.append(Text.literal(item.glyph()).setStyle(net.minecraft.text.Style.EMPTY
                .withFont(net.minecraft.util.Identifier.of(item.font())).withColor(item.font().equals("pocketmate:legendary_titles")?0xffffff:color)));
            prefix.append(" ");
        }
        return prefix.append(Text.literal(item.name()+" ").setStyle(net.minecraft.text.Style.EMPTY.withColor(color))).append(original.copy());
    }
    static ProfileStore adminTitles(MinecraftServer server){
        var store=stores.get(server);
        if(store==null)throw new IllegalStateException("칭호 저장소를 사용할 수 없습니다.");
        return store;
    }
    @Override public void onInitialize(){
        ServerLifecycleEvents.SERVER_STARTING.register(server->{
            try{stores.put(server,new ProfileStore(server.getSavePath(WorldSavePath.ROOT).resolve("data/pocketmate-profiles.json")));}
            catch(Exception error){LoggerFactory.getLogger("pocketmate-profile").error("Profile store unavailable; no ownership reset",error);}
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(server->{stores.remove(server);requests.clear();});
        ServerPlayConnectionEvents.DISCONNECT.register((handler,server)->requests.remove(handler.player.getUuid()));
        WebGuiBridge.listen(CHANNEL,(player,payload)->{MinecraftServer server=player.getServer();if(server!=null)server.execute(()->receive(server,player,payload));});
        CommandRegistrationCallback.EVENT.register((dispatcher,access,environment)->dispatcher.register(literal("pmprofile").requires(source->source.hasPermissionLevel(2))
            .then(literal("grantall").then(argument("player",EntityArgumentType.player()).then(literal("title").executes(context->{
                ProfileStore store=stores.get(context.getSource().getServer());
                try{
                    if(store==null)throw new IllegalStateException();
                    int added=store.grantAllTitles(EntityArgumentType.getPlayer(context,"player").getUuid());
                    context.getSource().sendFeedback(()->Text.literal("모든 칭호 지급 완료 · 새로 지급한 칭호 "+added+"개. 프로필 편집을 다시 열어주세요."),false);return 1;
                }catch(Exception failure){context.getSource().sendError(Text.literal("칭호를 지급하지 못했습니다. 프로필 저장 상태를 확인해주세요."));return 0;}
            }))))
            .then(literal("grant").then(argument("player",EntityArgumentType.player()).then(argument("kind",StringArgumentType.word()).suggests((context,builder)->{
                for(String kind:List.of("icon","title","banner"))builder.suggest(kind);return builder.buildFuture();
            }).then(argument("item",StringArgumentType.word()).suggests((context,builder)->{
                String kind=StringArgumentType.getString(context,"kind");for(var c:adminTitles(context.getSource().getServer()).catalog())if(c.kind().equals(kind))builder.suggest(c.id());return builder.buildFuture();
            }).executes(context->{
                ServerPlayerEntity target=EntityArgumentType.getPlayer(context,"player");ProfileStore store=stores.get(context.getSource().getServer());
                try{
                    if(store==null)throw new IllegalStateException();store.grant(target.getUuid(),StringArgumentType.getString(context,"kind"),StringArgumentType.getString(context,"item"));
                    context.getSource().sendFeedback(()->Text.literal("꾸미기 항목을 지급했습니다. 프로필 편집을 다시 열면 확인할 수 있습니다."),false);return 1;
                }catch(Exception failure){context.getSource().sendError(Text.literal("지급하지 못했습니다. 항목과 프로필 저장 상태를 확인해주세요."));return 0;}
            })))))));
    }
    private void receive(MinecraftServer server,ServerPlayerEntity player,String payload){
        String requestId="";
        try{
            if(payload==null||payload.length()>2048)throw new IllegalArgumentException();JsonObject request=JsonParser.parseString(payload).getAsJsonObject();
            requestId=string(request,"requestId",64);if(!requestId.matches("[A-Za-z0-9_-]{1,64}"))throw new IllegalArgumentException();
            ProfileStore store=stores.get(server);if(store==null){error(player,requestId,"프로필 저장소를 사용할 수 없습니다. 관리자에게 문의해주세요.");return;}
            UUID id=player.getUuid();long now=System.currentTimeMillis();Long last=requests.get(id);
            if(last!=null&&now-last<200){error(player,requestId,"잠시 후 다시 시도해주세요.");return;}requests.put(id,now);
            String action=string(request,"action",16);ProfileStore.Profile profile;
            if(action.equals("view"))profile=store.get(id);
            else if(action.equals("equip"))profile=store.equip(id,string(request,"icon",32),string(request,"title",32),string(request,"banner",32));
            else throw new IllegalArgumentException();
            JsonObject response=new JsonObject();response.addProperty("type","snapshot");response.addProperty("requestId",requestId);response.addProperty("playerId",id.toString());response.addProperty("playerName",NicknamesMod.name(player));
            response.add("profile",new Gson().toJsonTree(profile));response.add("catalog",new Gson().toJsonTree(store.catalog()));
            if(action.equals("equip"))response.addProperty("message","프로필카드를 저장했습니다.");WebGuiBridge.emit(player,CHANNEL,response.toString());
        }catch(ProfileStore.Denied denied){error(player,requestId,denied.getMessage());}
        catch(java.io.IOException failure){LoggerFactory.getLogger("pocketmate-profile").error("Profile save failed",failure);error(player,requestId,"저장에 실패했습니다. 착용 정보를 다시 확인해주세요.");}
        catch(RuntimeException invalid){error(player,requestId,"올바르지 않은 프로필 요청입니다.");}
    }
    private static String string(JsonObject request,String field,int max){JsonElement value=request.get(field);if(value==null||!value.isJsonPrimitive()||!value.getAsJsonPrimitive().isString())throw new IllegalArgumentException();String text=value.getAsString();if(text.isEmpty()||text.length()>max)throw new IllegalArgumentException();return text;}
    private static void error(ServerPlayerEntity player,String id,String message){JsonObject response=new JsonObject();response.addProperty("type","error");response.addProperty("requestId",id);response.addProperty("message",message);WebGuiBridge.emit(player,CHANNEL,response.toString());}
}
