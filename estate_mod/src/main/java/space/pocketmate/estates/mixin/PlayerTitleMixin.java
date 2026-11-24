package space.pocketmate.estates.mixin;

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import space.pocketmate.estates.ProfilesMod;

/** Decorate the sender name, preserving the signed chat body and vanilla delivery. */
@Mixin(PlayerEntity.class)
public abstract class PlayerTitleMixin {
    @Inject(method="getDisplayName",at=@At("RETURN"),cancellable=true)
    private void pocketmate$title(CallbackInfoReturnable<Text> result){
        if((Object)this instanceof ServerPlayerEntity player)
            result.setReturnValue(ProfilesMod.titledName(player,space.pocketmate.estates.NicknamesMod.display(player,result.getReturnValue())));
    }
}
