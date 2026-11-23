package space.pocketmate.webgui.mixin;

import com.mojang.blaze3d.systems.RenderSystem;
import org.lwjgl.opengl.GL11;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** WebGUI 2.0.0 on MC 1.21.1 draws its transparent texture without enabling alpha blending. */
@Mixin(targets = "land.webgui.WebViewScreen", remap = false)
public abstract class GuiTransparencyMixin {
    @Unique private boolean pocketmate$previousBlend;

    @Inject(method = {"method_25394", "render"}, at = @At("HEAD"), require = 1, remap = false)
    private void pocketmate$enableAlpha(CallbackInfo callback) {
        pocketmate$previousBlend = GL11.glIsEnabled(GL11.GL_BLEND);
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
    }

    @Inject(method = {"method_25394", "render"}, at = @At("RETURN"), require = 1, remap = false)
    private void pocketmate$restoreAlpha(CallbackInfo callback) {
        if (!pocketmate$previousBlend) RenderSystem.disableBlend();
    }
}
