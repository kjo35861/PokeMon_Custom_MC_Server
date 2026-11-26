package space.pocketmate.mega.mixin;

import com.pixelmonmod.pixelmon.api.pokemon.species.Stats;
import com.pixelmonmod.pixelmon.battles.controller.participants.PixelmonWrapper;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = PixelmonWrapper.class, remap = false)
public abstract class ZygardeHealthMixin {
    @Unique private int pocketmate$previousHealth;
    @Unique private int pocketmate$previousMax;
    @Unique private boolean pocketmate$adjustHealth;

    @Inject(method = "setForm(Lcom/pixelmonmod/pixelmon/api/pokemon/species/Stats;)V", at = @At("HEAD"), remap = false)
    private void pocketmate$beforeForm(Stats target, CallbackInfo callback) {
        var self = (PixelmonWrapper) (Object) this;
        pocketmate$adjustHealth = target != null && self.getBattleController() != null
            && !self.getBattleController().simulateMode() && !self.getBattleController().battleEnded()
            && self.getSpecies().getName().equals("Zygarde")
            && (target.getName().startsWith("mega") || self.getForm().getName().startsWith("mega"));
        if (pocketmate$adjustHealth) {
            pocketmate$previousHealth = self.getHealth();
            pocketmate$previousMax = self.getMaxHealth();
        }
    }

    @Inject(method = "setForm(Lcom/pixelmonmod/pixelmon/api/pokemon/species/Stats;)V", at = @At("RETURN"), remap = false)
    private void pocketmate$afterForm(Stats target, CallbackInfo callback) {
        if (!pocketmate$adjustHealth || pocketmate$previousMax <= 0) return;
        pocketmate$adjustHealth = false;
        var self = (PixelmonWrapper) (Object) this;
        self.recalculateMaxHP();
        if (self.getMaxHealth() == pocketmate$previousMax) return;
        int health = (int) Math.round((double) pocketmate$previousHealth / pocketmate$previousMax * self.getMaxHealth());
        if (pocketmate$previousHealth > 0) health = Math.max(1, health);
        self.setHealth(Math.min(self.getMaxHealth(), health));
        self.getBattleController().publishPokemonHealthUpdate(self, pocketmate$previousHealth);
    }
}
