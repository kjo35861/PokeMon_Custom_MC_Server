package space.pocketmate.estates.mixin;
import net.minecraft.block.PistonBlock;
import net.minecraft.block.piston.PistonHandler;
import net.minecraft.world.World;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import space.pocketmate.estates.MissionsMod;
@Mixin(PistonBlock.class)
public abstract class MissionPistonMixin {
 @Redirect(method="move",at=@At(value="INVOKE",target="Lnet/minecraft/block/piston/PistonHandler;calculatePush()Z"))
 private boolean pocketmate$moveGuard(PistonHandler handler,World world,BlockPos pos,Direction direction,boolean retracted){
  boolean result=handler.calculatePush();
  if(result&&!world.isClient())MissionsMod.pistonMove(world,handler.getMovedBlocks(),handler.getMotionDirection());
  return result;
 }
}
