package space.pocketmate.estates.client;

import java.lang.reflect.Method;
import net.minecraft.client.render.entity.EntityRenderer;
import net.minecraft.entity.Entity;
import net.minecraft.util.Identifier;

/** Xaero calls this method with the entity when resolving the icon variant. */
public final class PixelmonRadarVariant {
    private static final ClassValue<Method> SPRITE_GETTER = new ClassValue<>() {
        @Override
        protected Method computeValue(Class<?> type) {
            try {
                return type.getMethod("getSprite");
            } catch (NoSuchMethodException exception) {
                return null;
            }
        }
    };

    private PixelmonRadarVariant() {}

    public static Object getVariant(Identifier rendererTexture, EntityRenderer<?> renderer, Entity entity) {
        Method getter = SPRITE_GETTER.get(entity.getClass());
        if (getter == null) return rendererTexture;
        try {
            Object sprite = getter.invoke(entity);
            return sprite instanceof Identifier ? sprite : rendererTexture;
        } catch (ReflectiveOperationException exception) {
            return rendererTexture;
        }
    }
}
