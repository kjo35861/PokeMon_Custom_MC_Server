package space.pocketmate.estates.mixin;
import net.minecraft.item.BlockItem;
import net.minecraft.item.ItemPlacementContext;
import net.minecraft.util.ActionResult;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import space.pocketmate.estates.MissionsMod;
@Mixin(BlockItem.class)
public abstract class MissionBlockPlaceMixin {
 @Inject(method="place(Lnet/minecraft/item/ItemPlacementContext;)Lnet/minecraft/util/ActionResult;",at=@At("RETURN"))
 private void pocketmate$placed(ItemPlacementContext context,CallbackInfoReturnable<ActionResult> cir){
  if(cir.getReturnValue().isAccepted()&&!context.getWorld().isClient())MissionsMod.placed(context.getWorld(),context.getBlockPos(),context.getPlayer());
 }
}
