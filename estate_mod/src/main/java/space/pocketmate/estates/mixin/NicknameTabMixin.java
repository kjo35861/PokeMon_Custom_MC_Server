package space.pocketmate.estates.mixin;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
@Mixin(ServerPlayerEntity.class)
public abstract class NicknameTabMixin {
    @Inject(method="getPlayerListName",at=@At("RETURN"),cancellable=true)
    private void pocketmate$tab(CallbackInfoReturnable<Text> result){
        var player=(ServerPlayerEntity)(Object)this;String name=space.pocketmate.estates.NicknamesMod.name(player);
        if(!name.equals(player.getGameProfile().getName()))result.setReturnValue(Text.literal(name));
    }
}
