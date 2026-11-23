package space.pocketmate.estates;

import net.minecraft.server.network.ServerPlayerEntity;
import java.lang.reflect.Method;
import java.util.function.BiConsumer;

/**
 * The stable public WebGUI API, isolated from its Java-25 build-tool metadata.
 * Uses the real runtime ServerPlayer type; no private methods or client internals are accessed.
 */
final class WebGuiBridge {
    private static final Method LISTEN, EMIT;
    static {
        try {
            Class<?> api=Class.forName("land.webgui.api.WebviewApi");
            LISTEN=api.getMethod("onPageEvent",String.class,BiConsumer.class);
            EMIT=api.getMethod("emitToPage",ServerPlayerEntity.class,String.class,String.class);
        } catch(ReflectiveOperationException error){throw new IllegalStateException("Pocketmate Estates requires the WebGUI 2.0.0 public server API",error);}
    }
    static void listen(String channel,BiConsumer<ServerPlayerEntity,String> listener) {
        try {LISTEN.invoke(null,channel,listener);}
        catch(ReflectiveOperationException error){throw new IllegalStateException("Could not register WebGUI estate handler",error);}
    }
    static void emit(ServerPlayerEntity player,String event,String payload) {
        try {EMIT.invoke(null,player,event,payload);}
        catch(ReflectiveOperationException error){throw new IllegalStateException("Could not send estate response",error);}
    }
}
