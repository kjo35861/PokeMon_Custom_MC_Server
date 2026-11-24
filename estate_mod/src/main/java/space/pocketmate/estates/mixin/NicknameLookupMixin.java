package space.pocketmate.estates.mixin;
import net.minecraft.server.PlayerManager;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
@Mixin(PlayerManager.class)
public abstract class NicknameLookupMixin {
    @Shadow @Final private MinecraftServer server;
    @Inject(method="getPlayer(Ljava/lang/String;)Lnet/minecraft/server/network/ServerPlayerEntity;",at=@At("RETURN"),cancellable=true)
    private void pocketmate$alias(String name,CallbackInfoReturnable<ServerPlayerEntity> result){
        if(result.getReturnValue()!=null)return;
        var id=space.pocketmate.estates.NicknamesMod.resolve(server,name);
        if(id!=null)result.setReturnValue(((PlayerManager)(Object)this).getPlayer(id));
    }
}
