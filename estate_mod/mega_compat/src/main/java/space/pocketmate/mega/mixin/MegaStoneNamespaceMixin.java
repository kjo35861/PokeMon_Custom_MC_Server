package space.pocketmate.mega.mixin;

import com.google.gson.JsonParser;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Supplier;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "com.eeveeserver.mega.MegaStones", remap = false)
abstract class MegaStoneNamespaceMixin {
    @Unique
    private static Map<String, ResourceLocation> pocketmate$nativeStones;

    @Redirect(method = "<clinit>", at = @At(value = "INVOKE",
        target = "Lnet/neoforged/neoforge/registries/DeferredRegister;createItems(Ljava/lang/String;)Lnet/neoforged/neoforge/registries/DeferredRegister$Items;",
        remap = false), require = 1)
    private static DeferredRegister.Items pocketmate$registerStones(String legacyNamespace) {
        pocketmate$nativeStones = pocketmate$readNativeStones();
        var items = DeferredRegister.createItems("pocketmate_mega");
        for (int i = 1; i <= 128; i++) {
            String path = "mega_stone_" + i;
            var custom = ResourceLocation.fromNamespaceAndPath("pocketmate_mega", path);
            var replacement = pocketmate$nativeStones.get(path);
            items.addAlias(ResourceLocation.fromNamespaceAndPath(legacyNamespace, path),
                replacement == null ? custom : replacement);
            if (replacement != null) items.addAlias(custom, replacement);
        }
        return items;
    }

    @Redirect(method = "<clinit>", at = @At(value = "INVOKE",
        target = "Lnet/neoforged/neoforge/registries/DeferredRegister$Items;register(Ljava/lang/String;Ljava/util/function/Supplier;)Lnet/neoforged/neoforge/registries/DeferredItem;",
        remap = false), require = 1)
    private static DeferredItem<?> pocketmate$registerStone(DeferredRegister.Items registry, String path,
                                                            Supplier<? extends Item> factory) {
        var replacement = pocketmate$nativeStones.get(path);
        // Preserve the original indexed pool while leaving registration to Pixelmon.
        return replacement == null ? registry.register(path, factory) : DeferredItem.createItem(replacement);
    }

    @Unique
    private static Map<String, ResourceLocation> pocketmate$readNativeStones() {
        try (var stream = space.pocketmate.mega.PocketmateMegaBridge.class.getResourceAsStream("/pocketmate_native_stones.json")) {
            if (stream == null) throw new IllegalStateException("Missing native Mega Stone mappings");
            var json = JsonParser.parseReader(new InputStreamReader(stream, StandardCharsets.UTF_8)).getAsJsonObject();
            var result = new HashMap<String, ResourceLocation>();
            json.entrySet().forEach(entry -> result.put(entry.getKey(), ResourceLocation.parse(entry.getValue().getAsString())));
            return Map.copyOf(result);
        } catch (java.io.IOException exception) {
            throw new IllegalStateException("Could not read native Mega Stone mappings", exception);
        }
    }
}
