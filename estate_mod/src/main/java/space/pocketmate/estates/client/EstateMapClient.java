package space.pocketmate.estates.client;

import com.google.gson.*;
import space.pocketmate.estates.MapPixelCodec;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.MinecraftClient;
import net.minecraft.registry.RegistryKey;
import net.minecraft.world.World;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL15;
import org.lwjgl.opengl.GL21;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.util.*;

/** Read-only adapter to Xaero's already rendered surface-level map tiles. */
public final class EstateMapClient implements ClientModInitializer {
    private static final Logger LOG=LoggerFactory.getLogger("pocketmate-map");
    private static final Gson JSON=new Gson();
    private static final Map<String,Method> METHODS=new HashMap<>();
    private static final ArrayDeque<Tile> QUEUE=new ArrayDeque<>();
    private static final Map<Tile,Integer> SENT=new HashMap<>();
    private static Object session;
    private static String requestId="";
    private static int attempts;
    private static int passRemaining;
    private static long nextPass;
    private static boolean logged;
    private static boolean requestLogged;
    private static String lastMapSession="";
    private static int lastCx,lastCz,lastRadius;
    private record Tile(int x,int z) {}

    @Override public void onInitializeClient() { ClientTickEvents.END_CLIENT_TICK.register(EstateMapClient::tick); }

    public static void onSnapshot(String event,String payload) {
        if(!event.equals("pocketmate:estate"))return;
        try {
            JsonObject data=JsonParser.parseString(payload).getAsJsonObject();
            if(!"snapshot".equals(data.get("type").getAsString()))return;
            requestId=data.get("requestId").getAsString();
            if(!requestLogged){requestLogged=true;LOG.info("Estate page requested Xaero surface terrain");}
            int cx=data.get("centerX").getAsInt(),cz=data.get("centerZ").getAsInt();
            int radius=Math.clamp(data.get("radius").getAsInt(),2,48);
            String mapSession=data.has("mapSession")?data.get("mapSession").getAsString():requestId;
            // A wide view can take longer than the page's polling interval. Continue its queue
            // under the new request ID instead of repeatedly abandoning the outer tiles.
            if(mapSession.equals(lastMapSession)&&cx==lastCx&&cz==lastCz&&radius==lastRadius&&!QUEUE.isEmpty())return;
            lastMapSession=mapSession;lastCx=cx;lastCz=cz;lastRadius=radius;
            QUEUE.clear();SENT.clear();attempts=0;nextPass=0;
            ArrayList<Tile> tiles=new ArrayList<>();
            for(int z=Math.floorDiv(cz-radius,4);z<=Math.floorDiv(cz+radius,4);z++)
                for(int x=Math.floorDiv(cx-radius,4);x<=Math.floorDiv(cx+radius,4);x++)tiles.add(new Tile(x,z));
            tiles.sort(Comparator.comparingInt(t->Math.abs(t.x-Math.floorDiv(cx,4))+Math.abs(t.z-Math.floorDiv(cz,4))));
            QUEUE.addAll(tiles);passRemaining=QUEUE.size();
        } catch(RuntimeException ignored) { /* Non-estate events and malformed server data never affect gameplay. */ }
    }

    private static Object invoke(Object target,String method,Class<?>[] types,Object... args) throws ReflectiveOperationException {
        String key=target.getClass().getName()+"#"+method+Arrays.toString(types);
        Method found=METHODS.get(key);
        if(found==null){found=target.getClass().getMethod(method,types);METHODS.put(key,found);}
        return found.invoke(target,args);
    }
    private static Object call(Object target,String method,Object... args) throws ReflectiveOperationException {
        Class<?>[] types=new Class<?>[args.length];for(int i=0;i<args.length;i++)types[i]=args[i] instanceof Integer?int.class:args[i].getClass();
        return invoke(target,method,types,args);
    }
    private static void emit(JsonObject data) throws ReflectiveOperationException {
        data.addProperty("requestId",requestId);
        Class.forName("land.webgui.WebviewClientEmit").getMethod("dispatch",String.class,String.class).invoke(null,"pocketmate:terrain",JSON.toJson(data));
    }
    private static void status(String state,String message) throws ReflectiveOperationException {
        JsonObject data=new JsonObject();data.addProperty("type","status");data.addProperty("state",state);data.addProperty("message",message);emit(data);
    }
    private static void tick(MinecraftClient client) {
        if(client.world==null||client.player==null){QUEUE.clear();SENT.clear();session=null;lastMapSession="";return;}
        if(QUEUE.isEmpty()||System.currentTimeMillis()<nextPass)return;
        try {
            if(!FabricLoader.getInstance().isModLoaded("xaeroworldmap")){status("missing","Xaero 월드맵을 설치하면 지형 지도가 표시됩니다.");QUEUE.clear();return;}
            Object current=Class.forName("xaero.map.WorldMapSession").getMethod("getCurrentSession").invoke(null);
            if(current==null){nextPass=System.currentTimeMillis()+700;return;}
            if(session!=current){session=current;SENT.clear();}
            Object processor=call(session,"getMapProcessor"),world=call(processor,"getMapWorld");
            Object dimension=invoke(world,"getDimension",new Class<?>[]{RegistryKey.class},World.OVERWORLD);
            if(dimension==null){nextPass=System.currentTimeMillis()+700;return;}
            Object manager=call(dimension,"getLayeredMapRegions");
            int processed=0;
            // At most two 64x64 readbacks per client tick. No Minecraft chunks are loaded/generated here.
            while(processed<2&&passRemaining>0&&!QUEUE.isEmpty()) {
                Tile tile=QUEUE.removeFirst();processed++;passRemaining--;
                // Xaero reserves MAX_VALUE for the surface. Zero is a subterranean layer.
                Object region=call(manager,"getLeaf",Integer.MAX_VALUE,Math.floorDiv(tile.x,8),Math.floorDiv(tile.z,8));
                if(region==null){QUEUE.addLast(tile);continue;}
                Object texture=call(region,"getTexture",Math.floorMod(tile.x,8),Math.floorMod(tile.z,8));
                if(texture==null){QUEUE.addLast(tile);continue;}
                int[] pixels=readPixels(texture);
                if(pixels==null){QUEUE.addLast(tile);continue;}
                int hash=Arrays.hashCode(pixels);
                if(!Objects.equals(SENT.get(tile),hash)) {
                    BufferedImage image=new BufferedImage(64,64,BufferedImage.TYPE_INT_ARGB);image.setRGB(0,0,64,64,pixels,0,64);
                    ByteArrayOutputStream bytes=new ByteArrayOutputStream();ImageIO.write(image,"png",bytes);
                    JsonObject data=new JsonObject();data.addProperty("type","tile");data.addProperty("source","xaero");
                    data.addProperty("tileX",tile.x);data.addProperty("tileZ",tile.z);data.addProperty("blocks",64);
                    data.addProperty("png",Base64.getEncoder().encodeToString(bytes.toByteArray()));emit(data);SENT.put(tile,hash);
                    if(!logged){logged=true;LOG.info("Xaero terrain bridge delivered real 64x64 surface map tile");}
                }
            }
            if(passRemaining<=0){attempts++;passRemaining=QUEUE.size();nextPass=System.currentTimeMillis()+350;}
            if(attempts==2&&SENT.isEmpty())status("waiting","Xaero 지형 기록 대기 · M으로 월드맵을 한 번 열어주세요.");
            if(attempts>12){status(SENT.isEmpty()?"waiting":"ready",SENT.isEmpty()?"Xaero 지형 기록 대기 · M으로 월드맵을 한 번 열어주세요.":"Xaero 월드맵 · 미탐색 지역은 안개로 표시됩니다.");QUEUE.clear();}
        } catch(Exception error) {
            if(!logged){LOG.warn("Xaero terrain adapter unavailable; ownership remains server-authoritative",error);logged=true;}
            try{status("unavailable","Xaero 지도 연결을 확인해주세요. 소유권 조회는 계속 사용할 수 있습니다.");}catch(Exception ignored){}
            QUEUE.clear();
        }
    }
    private static int[] readPixels(Object texture) throws ReflectiveOperationException {
        int id=(Integer)call(texture,"getGlColorTexture");
        ByteBuffer buffer;
        boolean raw=false;
        if(id>0) {
            int previous=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D),pack=GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING);
            int alignment=GL11.glGetInteger(GL11.GL_PACK_ALIGNMENT),rowLength=GL11.glGetInteger(GL11.GL_PACK_ROW_LENGTH);
            int skipRows=GL11.glGetInteger(GL11.GL_PACK_SKIP_ROWS),skipPixels=GL11.glGetInteger(GL11.GL_PACK_SKIP_PIXELS);
            buffer=BufferUtils.createByteBuffer(64*64*4);
            try {
                GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);GL11.glBindTexture(GL11.GL_TEXTURE_2D,id);
                if(GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH)!=64||GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT)!=64)return null;
                GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT,1);GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,0);
                GL11.glPixelStorei(GL11.GL_PACK_SKIP_ROWS,0);GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,0);
                GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,buffer);
            } finally {
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,previous);GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,pack);
                GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT,alignment);GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,rowLength);
                GL11.glPixelStorei(GL11.GL_PACK_SKIP_ROWS,skipRows);GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,skipPixels);
            }
        } else {
            if((Boolean)call(texture,"isColorBufferCompressed")||(Integer)call(texture,"getColorBufferFormat")==-1)return null;
            buffer=(ByteBuffer)call(texture,"getDirectColorBuffer");if(buffer==null||buffer.capacity()<16384)return null;raw=true;
        }
        int[] pixels=new int[4096];
        for(int i=0;i<4096;i++) {
            int r,g,b,a;
            if(raw){int value=buffer.getInt(i*4);r=value>>>8&255;g=value>>>16&255;b=value>>>24&255;a=value&255;}
            else{r=buffer.get(i*4)&255;g=buffer.get(i*4+1)&255;b=buffer.get(i*4+2)&255;a=buffer.get(i*4+3)&255;}
            // Xaero map.fsh uses alpha as emitted light, not opacity. Render a daylight terrain image.
            pixels[i]=MapPixelCodec.daylightArgb(r,g,b,a);
        }
        return pixels;
    }
}
