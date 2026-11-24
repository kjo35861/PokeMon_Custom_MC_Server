package space.pocketmate.estates.client;
import com.google.gson.*;
import net.minecraft.client.MinecraftClient;
import net.minecraft.registry.Registries;
import net.minecraft.util.Identifier;
import java.util.*;

/** Read small textures from the installed client/resource pack; no game textures are bundled. */
public final class ShopAssetsClient {
 public static void onSnapshot(String event,String payload){
  if(!event.equals("pocketmate:shop"))return;
  try{
   JsonObject data=JsonParser.parseString(payload).getAsJsonObject();if(!data.has("items")||!data.has("requestId"))return;
   MinecraftClient client=MinecraftClient.getInstance();client.execute(()->{
    try{
     JsonObject out=new JsonObject();out.addProperty("requestId",data.get("requestId").getAsString());JsonObject icons=new JsonObject();int total=0;
     for(JsonElement value:data.getAsJsonArray("items")){
      String name=value.getAsJsonObject().get("id").getAsString();Identifier id=Identifier.of(name);if(!id.getNamespace().equals("minecraft"))continue;
      String path=id.getPath();List<String> paths=new ArrayList<>(List.of("item/"+path,"block/"+path,"block/"+path+"_side","block/"+path+"_top"));
      if(path.equals("grass_block"))paths.add("block/grass_block_top");
      for(String candidate:paths){var resource=client.getResourceManager().getResource(Identifier.ofVanilla("textures/"+candidate+".png"));if(resource.isEmpty())continue;
       try(var stream=resource.get().getInputStream()){byte[] bytes=stream.readNBytes(16385);if(bytes.length>16384||total+bytes.length>48000)break;total+=bytes.length;icons.addProperty(name,"data:image/png;base64,"+Base64.getEncoder().encodeToString(bytes));}break;
      }
     }
     out.add("icons",icons);Class.forName("land.webgui.WebviewClientEmit").getMethod("dispatch",String.class,String.class).invoke(null,"pocketmate:shop-assets",out.toString());
    }catch(Exception ignored){}
   });
  }catch(RuntimeException ignored){}
 }
}
