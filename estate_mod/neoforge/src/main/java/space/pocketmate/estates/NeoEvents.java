package space.pocketmate.estates;

import com.mojang.brigadier.CommandDispatcher;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.network.packet.CustomPayload;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.command.CommandRegistryAccess;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.server.ServerStartingEvent;
import net.neoforged.neoforge.event.server.ServerStoppedEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;

public final class NeoEvents {
    static void starting(Consumer<MinecraftServer> callback) { NeoForge.EVENT_BUS.addListener((ServerStartingEvent e) -> callback.accept(e.getServer())); }
    static void stopped(Consumer<MinecraftServer> callback) { NeoForge.EVENT_BUS.addListener((ServerStoppedEvent e) -> callback.accept(e.getServer())); }
    static void beforeTick(Consumer<MinecraftServer> callback) { NeoForge.EVENT_BUS.addListener((ServerTickEvent.Pre e) -> callback.accept(e.getServer())); }
    static void afterTick(Consumer<MinecraftServer> callback) { NeoForge.EVENT_BUS.addListener((ServerTickEvent.Post e) -> callback.accept(e.getServer())); }
    static void join(BiConsumer<ServerPlayerEntity, MinecraftServer> callback) {
        NeoForge.EVENT_BUS.addListener((PlayerEvent.PlayerLoggedInEvent e) -> {
            if (e.getEntity() instanceof ServerPlayerEntity p) callback.accept(p,p.getServer());
        });
    }
    static void leave(BiConsumer<ServerPlayerEntity, MinecraftServer> callback) {
        NeoForge.EVENT_BUS.addListener((PlayerEvent.PlayerLoggedOutEvent e) -> {
            if (e.getEntity() instanceof ServerPlayerEntity p) callback.accept(p,p.getServer());
        });
    }
    interface Commands {
        void accept(CommandDispatcher<ServerCommandSource> dispatcher, CommandRegistryAccess access, CommandManager.RegistrationEnvironment environment);
    }
    static void commands(Commands callback) {
        NeoForge.EVENT_BUS.addListener((RegisterCommandsEvent e) -> callback.accept(e.getDispatcher(),e.getBuildContext(),e.getCommandSelection()));
    }
    public interface BreakCallback {
        void accept(World world, ServerPlayerEntity player, BlockPos position, BlockState state, BlockEntity entity);
    }
    private static BreakCallback afterBreak;
    static void blockBroken(BreakCallback callback) { afterBreak = callback; }
    public static void fireBlockBroken(World world, ServerPlayerEntity player, BlockPos pos, BlockState state, BlockEntity entity) {
        if (afterBreak != null) afterBreak.accept(world,player,pos,state,entity);
    }

    private static Consumer<NicknamePayload> nicknameReceiver = payload -> {};
    public static void setNicknameReceiver(Consumer<NicknamePayload> receiver) { nicknameReceiver = receiver; }
    static void registerPayloads(RegisterPayloadHandlersEvent event) {
        event.registrar("1").optional().playToClient(NicknamePayload.ID,NicknamePayload.CODEC,
            (payload, context) -> nicknameReceiver.accept(payload));
    }
    static boolean canSendNickname(ServerPlayerEntity player) {
        return player.networkHandler.hasChannel(NicknamePayload.ID);
    }
    static void sendNickname(ServerPlayerEntity player, CustomPayload payload) { PacketDistributor.sendToPlayer(player,payload); }
}
