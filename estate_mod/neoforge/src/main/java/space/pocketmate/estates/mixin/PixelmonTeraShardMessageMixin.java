package space.pocketmate.estates.mixin;

import net.minecraft.entity.Entity;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Pseudo
@Mixin(targets="com.pixelmonmod.pixelmon.entities.pixelmon.interactions.InteractionTeraShard", remap=false)
abstract class PixelmonTeraShardMessageMixin {
    @Redirect(method="processInteract", at=@At(value="INVOKE", target="Lcom/pixelmonmod/pixelmon/comm/ChatHandler;sendChat(Lnet/minecraft/world/entity/Entity;Ljava/lang/String;[Ljava/lang/Object;)V", remap=false), require=1)
    private void pocketmate$sendTeraMessage(Entity recipient, String key, Object[] args) {
        if (!(recipient instanceof ServerPlayerEntity player)) return;
        if (key.startsWith("pixelmon.interaction.tera_shard.not_enough.") && args.length == 2
                && player.getClientOptions().language().equalsIgnoreCase("ko_kr")) {
            Text name = args[1] instanceof Text text ? text : Text.literal(String.valueOf(args[1]));
            player.sendMessage(Text.empty().append(name)
                    .append("의 테라스탈 타입을 바꾸려면 테라스탈조각이 " + args[0] + "개 필요합니다."), false);
            return;
        }
        player.sendMessage(Text.translatable(key,args),false);
    }
}
