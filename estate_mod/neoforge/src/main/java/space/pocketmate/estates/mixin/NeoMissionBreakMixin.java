package space.pocketmate.estates.mixin;

import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.network.ServerPlayerInteractionManager;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.math.BlockPos;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import space.pocketmate.estates.NeoEvents;

@Mixin(ServerPlayerInteractionManager.class)
abstract class NeoMissionBreakMixin {
    @Shadow protected ServerWorld world;
    @Shadow @Final protected ServerPlayerEntity player;
    @Unique private BlockState pocketmate$before;
    @Unique private BlockEntity pocketmate$entity;

    @Inject(method="tryBreakBlock",at=@At("HEAD"))
    private void pocketmate$remember(BlockPos pos,CallbackInfoReturnable<Boolean> ci) {
        pocketmate$before = world.getBlockState(pos);
        pocketmate$entity = world.getBlockEntity(pos);
    }
    @Inject(method="tryBreakBlock",at=@At("RETURN"))
    private void pocketmate$count(BlockPos pos,CallbackInfoReturnable<Boolean> ci) {
        BlockState before = pocketmate$before;
        BlockEntity entity = pocketmate$entity;
        pocketmate$before = null;
        pocketmate$entity = null;
        if (ci.getReturnValueZ() && before != null && world.getBlockState(pos) != before)
            NeoEvents.fireBlockBroken(world,player,pos,before,entity);
    }
}
