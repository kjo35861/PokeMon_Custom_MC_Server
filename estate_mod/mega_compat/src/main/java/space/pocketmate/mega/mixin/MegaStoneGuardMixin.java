package space.pocketmate.mega.mixin;

import com.eeveeserver.mega.GenericMegaStone;
import com.pixelmonmod.api.pokemon.PokemonSpecification;
import com.pixelmonmod.api.pokemon.PokemonSpecificationProxy;
import com.pixelmonmod.pixelmon.api.config.PixelmonConfigProxy;
import com.pixelmonmod.pixelmon.entities.pixelmon.PixelmonEntity;
import com.pixelmonmod.pixelmon.init.registry.PixelmonDataComponents;
import com.pixelmonmod.pixelmon.items.HeldItemInteractionResult;
import com.pixelmonmod.pixelmon.items.component.MegaEvolution;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import java.util.List;

@Mixin(value = GenericMegaStone.class, remap = false)
public abstract class MegaStoneGuardMixin {
    @Inject(method = "interact", at = @At("HEAD"), cancellable = true, remap = false)
    private void pocketmate$checkCurrentForm(PixelmonEntity entity, ItemStack stack, Player player,
                                            CallbackInfoReturnable<HeldItemInteractionResult> callback) {
        var pokemon = entity.getPokemon();
        if (pokemon.getForm().getName().startsWith("mega")) {
            callback.setReturnValue(HeldItemInteractionResult.FAILURE_AND_RETAIN);
            return;
        }
        var target = pokemon.getForm().getMegaForm((Item) (Object) this);
        if (target.isEmpty()) {
            callback.setReturnValue(HeldItemInteractionResult.FAILURE_AND_RETAIN);
            return;
        }
        // A shared stone may lead to distinct targets so the original base form
        // survives reversion (Tatsugiri colours, Zygarde 10% versus 50%).
        var spec = (PokemonSpecification) PokemonSpecificationProxy.create(new String[]{pokemon.getSpecies().getName()}).get();
        stack.set(PixelmonDataComponents.MEGA_EVOLUTION,
            new MegaEvolution(List.of(spec), target.get().getName(), PixelmonConfigProxy.getItems().getDefaultMegaStoneTime()));
        // Continue the original implementation: key stone, ownership, cooldown,
        // consumption, event cancellation and native temporary evolution stay intact.
    }
}
