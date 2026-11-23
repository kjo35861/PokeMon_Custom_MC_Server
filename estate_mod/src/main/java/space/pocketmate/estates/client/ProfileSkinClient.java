package space.pocketmate.estates.client;

import com.google.gson.*;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.MinecraftClient;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.*;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.util.Base64;

/** Face + hat from Minecraft skin textures, including cached/offline player profiles. */
public final class ProfileSkinClient implements ClientModInitializer {
    private static final java.util.LinkedHashMap<java.util.UUID,Target> targets=new java.util.LinkedHashMap<>();
    private static Object connection;
    private static int loading;
    private static final class Target {
        final java.util.UUID id;final String name;
        long until,next,fetchAfter;String sent="";
        net.minecraft.util.Identifier texture;
        boolean fetching;
        Target(java.util.UUID id,String name){this.id=id;this.name=name;}
    }
    public static void onSnapshot(String event,String payload){
        if(!event.equals("pocketmate:profile")&&!event.equals("pocketmate:estate"))return;
        try{
            JsonObject data=JsonParser.parseString(payload).getAsJsonObject();String type=data.get("type").getAsString();
            java.util.List<String[]> people=new java.util.ArrayList<>();
            if(type.equals("snapshot")&&data.has("playerId"))people.add(new String[]{data.get("playerId").getAsString(),data.has("playerName")?data.get("playerName").getAsString():"Player"});
            for(String field:java.util.List.of("members","players","outgoingInvites"))if(data.has(field))for(JsonElement entry:data.getAsJsonArray(field)){
                JsonObject person=entry.getAsJsonObject();
                if(person.has("appearance")&&"skin".equals(person.getAsJsonObject("appearance").get("icon").getAsString()))people.add(new String[]{person.get("id").getAsString(),person.get("name").getAsString()});
            }
            MinecraftClient client=MinecraftClient.getInstance();
            client.execute(()->{
                if(client.world==null||client.getNetworkHandler()==null)return;
                prepare(client);
                for(String[] person:people){
                    try{
                        java.util.UUID id=java.util.UUID.fromString(person[0]);Target target=targets.computeIfAbsent(id,key->new Target(key,person[1]));
                        target.until=System.currentTimeMillis()+45000;target.next=0;target.sent="";
                        if(targets.size()>96)targets.remove(targets.keySet().iterator().next());
                    }catch(IllegalArgumentException ignored){}
                }
            });
        }catch(RuntimeException ignored){}
    }
    @Override public void onInitializeClient(){ClientTickEvents.END_CLIENT_TICK.register(ProfileSkinClient::tick);}
    private static void prepare(MinecraftClient client){
        Object current=client.getNetworkHandler();
        if(connection!=current){connection=current;targets.clear();loading=0;}
    }
    private static void tick(MinecraftClient client){
        prepare(client);
        if(client.player==null||client.world==null){targets.clear();return;}
        long now=System.currentTimeMillis();int faces=0;
        targets.values().removeIf(target->target.until<now);
        for(Target target:targets.values()){
            if(now<target.next)continue;target.next=now+1500;
            try{
                var entry=client.getNetworkHandler().getPlayerListEntry(target.id);
                if(target.id.equals(client.player.getUuid()))target.texture=client.player.getSkinTextures().texture();
                else if(entry!=null)target.texture=entry.getSkinTextures().texture();
                else if(!target.fetching&&now>=target.fetchAfter&&loading<2){
                    target.fetching=true;loading++;target.fetchAfter=now+120000;Object expected=connection;
                    java.util.concurrent.CompletableFuture.supplyAsync(()->{
                        var result=client.getSessionService().fetchProfile(target.id,true);
                        return result==null?new com.mojang.authlib.GameProfile(target.id,target.name):result.profile();
                    },net.minecraft.util.Util.getIoWorkerExecutor()).thenCompose(profile->client.getSkinProvider().fetchSkinTextures(profile)).whenComplete((textures,error)->client.execute(()->{
                        if(connection!=expected)return;loading--;target.fetching=false;
                        if(targets.get(target.id)!=target)return;
                        target.texture=textures!=null?textures.texture():net.minecraft.client.util.DefaultSkinHelper.getSkinTextures(target.id).texture();target.next=0;
                    }));
                }
                if(target.texture==null){if(!target.fetching)target.next=now+100;continue;}
                if(target.sent.equals(target.texture.toString()))continue;
                if(faces>=2){target.next=now;continue;}
                int id=client.getTextureManager().getTexture(target.texture).getGlId();BufferedImage image=face(id);
                if(image==null)continue;faces++;
                ByteArrayOutputStream bytes=new ByteArrayOutputStream();ImageIO.write(image,"png",bytes);
                JsonObject data=new JsonObject();data.addProperty("playerId",target.id.toString());data.addProperty("png",Base64.getEncoder().encodeToString(bytes.toByteArray()));
                Class.forName("land.webgui.WebviewClientEmit").getMethod("dispatch",String.class,String.class).invoke(null,"pocketmate:profile-skin",data.toString());target.sent=target.texture.toString();
            }catch(Exception ignored){ /* A temporary skin outage leaves the readable initial and retries later. */ }
        }
    }
    private static BufferedImage face(int id){
        if(id<=0)return null;
        int previous=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D),pack=GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING);
        int alignment=GL11.glGetInteger(GL11.GL_PACK_ALIGNMENT),row=GL11.glGetInteger(GL11.GL_PACK_ROW_LENGTH),skipRows=GL11.glGetInteger(GL11.GL_PACK_SKIP_ROWS),skipPixels=GL11.glGetInteger(GL11.GL_PACK_SKIP_PIXELS);
        try{
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);GL11.glBindTexture(GL11.GL_TEXTURE_2D,id);
            int width=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH),height=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT);
            if(width<64||width>1024||width%64!=0||height<width/2||height>1024)return null;
            ByteBuffer pixels=BufferUtils.createByteBuffer(width*height*4);GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT,1);GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,0);GL11.glPixelStorei(GL11.GL_PACK_SKIP_ROWS,0);GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,0);
            GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,pixels);
            int unit=width/64,size=8*unit;BufferedImage image=new BufferedImage(size,size,BufferedImage.TYPE_INT_ARGB);
            for(int y=0;y<size;y++)for(int x=0;x<size;x++){
                int base=((8*unit+y)*width+8*unit+x)*4,hat=((8*unit+y)*width+40*unit+x)*4;
                int a=pixels.get(hat+3)&255,r=blend(pixels,base,hat,0,a),g=blend(pixels,base,hat,1,a),b=blend(pixels,base,hat,2,a);
                image.setRGB(x,y,0xff000000|r<<16|g<<8|b);
            }
            return image;
        }finally{
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,previous);GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,pack);GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT,alignment);GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,row);GL11.glPixelStorei(GL11.GL_PACK_SKIP_ROWS,skipRows);GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,skipPixels);
        }
    }
    private static int blend(ByteBuffer pixels,int base,int hat,int channel,int alpha){return ((pixels.get(hat+channel)&255)*alpha+(pixels.get(base+channel)&255)*(255-alpha)+127)/255;}
}
