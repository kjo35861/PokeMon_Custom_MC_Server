package space.pocketmate.estates;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.minecraft.util.WorldSavePath;
import com.mojang.brigadier.arguments.StringArgumentType;
import static net.minecraft.server.command.CommandManager.*;
import java.util.*;
public final class NicknamesMod implements ModInitializer {
    private static final Map<MinecraftServer,NicknameStore> stores=new IdentityHashMap<>();
    public static String name(MinecraftServer server,UUID id,String fallback){var store=stores.get(server);String name=store==null?null:store.get(id);return name==null?fallback:name;}
    public static String name(ServerPlayerEntity p){return name(p.getServer(),p.getUuid(),p.getGameProfile().getName());}
    public static UUID resolve(MinecraftServer server,String name){var store=stores.get(server);return store==null?null:store.resolve(name);}
    public static Text display(ServerPlayerEntity p,Text original){String name=name(p);return name.equals(p.getGameProfile().getName())?original:Text.literal(name).setStyle(original.getStyle());}
    private static void sync(ServerPlayerEntity p,String message){
        var store=stores.get(p.getServer());boolean required=store!=null&&store.get(p.getUuid())==null;
        if(ServerPlayNetworking.canSend(p,NicknamePayload.ID))ServerPlayNetworking.send(p,new NicknamePayload(required,message));
        if(required)p.sendMessage(Text.literal("처음 오셨군요! /닉네임 설정 <이름> 으로 닉네임을 지정해주세요. 한글 가능 · 2~12자"),false);
    }
    @Override public void onInitialize(){
        PayloadTypeRegistry.playS2C().register(NicknamePayload.ID,NicknamePayload.CODEC);
        ServerLifecycleEvents.SERVER_STARTING.register(server->{try{stores.put(server,new NicknameStore(server.getSavePath(WorldSavePath.ROOT).resolve("data/pocketmate-nicknames.json")));}catch(Exception e){org.slf4j.LoggerFactory.getLogger("pocketmate-nicknames").error("Nickname store unavailable; refusing reset",e);}});
        ServerLifecycleEvents.SERVER_STOPPED.register(stores::remove);
        ServerPlayConnectionEvents.JOIN.register((handler,sender,server)->sync(handler.player,""));
        CommandRegistrationCallback.EVENT.register((dispatcher,access,environment)->{
            var command=literal("닉네임").executes(c->{sync(c.getSource().getPlayerOrThrow(),"");return 1;})
                .then(literal("설정").then(argument("name",StringArgumentType.greedyString()).executes(c->{
                    var player=c.getSource().getPlayerOrThrow();var store=stores.get(c.getSource().getServer());
                    try{
                        if(store==null)throw new IllegalArgumentException("닉네임 저장소를 사용할 수 없습니다.");
                        Map<UUID,String> accounts=new HashMap<>();for(var p:c.getSource().getServer().getPlayerManager().getPlayerList())accounts.put(p.getUuid(),p.getGameProfile().getName());
                        store.register(player.getUuid(),StringArgumentType.getString(c,"name"),accounts);
                        player.getServer().getPlayerManager().sendToAll(new net.minecraft.network.packet.s2c.play.PlayerListS2CPacket(net.minecraft.network.packet.s2c.play.PlayerListS2CPacket.Action.UPDATE_DISPLAY_NAME,player));
                        player.sendMessage(Text.literal("닉네임을 "+name(player)+"(으)로 지정했습니다."),false);sync(player,"");return 1;
                    }catch(Exception error){String message=error instanceof IllegalArgumentException?error.getMessage():"저장에 실패했습니다. 다시 시도해주세요.";c.getSource().sendError(Text.literal(message));sync(player,message);return 0;}
                })));
            dispatcher.register(command);
        });
    }
}
