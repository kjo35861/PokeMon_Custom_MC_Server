package space.pocketmate.estates.client;

import com.google.gson.*;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.systems.VertexSorter;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.resource.ResourceManagerHelper;
import net.fabricmc.fabric.api.resource.SimpleSynchronousResourceReloadListener;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gl.*;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.render.*;
import net.minecraft.client.texture.NativeImage;
import net.minecraft.client.util.BufferAllocator;
import net.minecraft.item.ItemStack;
import net.minecraft.registry.Registries;
import net.minecraft.resource.*;
import net.minecraft.util.Identifier;
import org.joml.Matrix4f;
import org.lwjgl.opengl.*;
import java.util.*;

/** Render the actual resource-pack GUI item model, never a flat block texture. */
public final class ShopAssetsClient implements ClientModInitializer {
 private record Job(String requestId,ArrayDeque<String> ids){}
 private static final ArrayDeque<Job> jobs=new ArrayDeque<>();
 private static final LinkedHashMap<String,String> cache=new LinkedHashMap<>(128,.75f,true);
 private static long lastWarning;
 @Override public void onInitializeClient(){
  ClientTickEvents.END_CLIENT_TICK.register(ShopAssetsClient::tick);
  ResourceManagerHelper.get(ResourceType.CLIENT_RESOURCES).registerReloadListener(new SimpleSynchronousResourceReloadListener(){
   public Identifier getFabricId(){return Identifier.of("pocketmate","shop_icons");}
   public void reload(ResourceManager manager){MinecraftClient.getInstance().execute(()->{cache.clear();jobs.clear();});}
  });
 }
 public static void onSnapshot(String event,String payload){
  if(!event.equals("pocketmate:shop"))return;
  try{
   JsonObject data=JsonParser.parseString(payload).getAsJsonObject();if(!data.has("items")||!data.has("requestId"))return;
   ArrayDeque<String> ids=new ArrayDeque<>();for(JsonElement value:data.getAsJsonArray("items")){if(ids.size()>=24)break;String id=value.getAsJsonObject().get("id").getAsString();Identifier.of(id);ids.add(id);}
   String requestId=data.get("requestId").getAsString();MinecraftClient.getInstance().execute(()->{if(jobs.size()>=16)jobs.removeFirst();jobs.add(new Job(requestId,ids));});
  }catch(RuntimeException ignored){}
 }
 private static void tick(MinecraftClient client){
  if(client.world==null){jobs.clear();return;}if(jobs.isEmpty()||!RenderSystem.isOnRenderThread())return;
  Job job=jobs.peek();JsonObject icons=new JsonObject();int handled=0;
  while(!job.ids.isEmpty()&&handled<2){
   handled++;String id=job.ids.removeFirst();String png=cache.get(id);
   if(png==null)try{Identifier key=Identifier.of(id);if(!Registries.ITEM.containsId(key))continue;png=render(client,new ItemStack(Registries.ITEM.get(key)));cache.put(id,png);if(cache.size()>1024)cache.remove(cache.keySet().iterator().next());}
   catch(Exception|LinkageError error){if(System.currentTimeMillis()-lastWarning>30000){lastWarning=System.currentTimeMillis();org.slf4j.LoggerFactory.getLogger("pocketmate-shop").warn("Unable to render shop item {}",id,error);}}
   if(png!=null)icons.addProperty(id,png);
  }
  if(job.ids.isEmpty())jobs.removeFirst();if(icons.isEmpty())return;
  JsonObject out=new JsonObject();out.addProperty("requestId",job.requestId);out.add("icons",icons);
  try{Class.forName("land.webgui.WebviewClientEmit").getMethod("dispatch",String.class,String.class).invoke(null,"pocketmate:shop-assets",out.toString());}catch(ReflectiveOperationException ignored){}
 }
 private static String render(MinecraftClient client,ItemStack stack)throws Exception{
  try(State state=new State();BufferAllocator allocator=new BufferAllocator(16384)){
   SimpleFramebuffer target=new SimpleFramebuffer(64,64,true,MinecraftClient.IS_SYSTEM_MAC);
   try{
    target.setClearColor(0,0,0,0);RenderSystem.disableScissor();RenderSystem.depthMask(true);target.clear(MinecraftClient.IS_SYSTEM_MAC);target.beginWrite(true);
    RenderSystem.setProjectionMatrix(new Matrix4f().setOrtho(0,64,64,0,1000,21000),VertexSorter.BY_Z);
    RenderSystem.getModelViewStack().pushMatrix();
    try{
     RenderSystem.getModelViewStack().identity().translate(0,0,-11000);RenderSystem.applyModelViewMatrix();RenderSystem.setShaderColor(1,1,1,1);
     RenderSystem.enableDepthTest();RenderSystem.enableBlend();RenderSystem.defaultBlendFunc();DiffuseLighting.enableGuiDepthLighting();
     VertexConsumerProvider.Immediate buffers=VertexConsumerProvider.immediate(allocator);DrawContext context=new DrawContext(client,buffers);context.getMatrices().scale(4,4,1);context.drawItem(stack,0,0);context.draw();
     GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,0);GL11.glPixelStorei(GL11.GL_PACK_SKIP_ROWS,0);GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,0);
     RenderSystem.bindTexture(target.getColorAttachment());
     try(NativeImage image=new NativeImage(64,64,false)){image.loadFromTextureImage(0,false);image.mirrorVertically();return "data:image/png;base64,"+Base64.getEncoder().encodeToString(image.getBytes());}
    }finally{RenderSystem.getModelViewStack().popMatrix();RenderSystem.applyModelViewMatrix();}
   }finally{target.delete();}
  }
 }
 /** Restore GL bindings and RenderSystem's cached state even when a model fails. */
 private static final class State implements AutoCloseable{
  final int draw=GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING),read=GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING),program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM),active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
  final int[] viewport=new int[4],scissor=new int[4],textures=new int[12],bindings=new int[12];
  final float[] color=RenderSystem.getShaderColor().clone(),clear=new float[4];
  final Matrix4f projection=new Matrix4f(RenderSystem.getProjectionMatrix()),texture=new Matrix4f(RenderSystem.getTextureMatrix());
  final VertexSorter sorter=RenderSystem.getVertexSorting();final ShaderProgram shader=RenderSystem.getShader();
  final boolean blend=GL11.glIsEnabled(GL11.GL_BLEND),depth=GL11.glIsEnabled(GL11.GL_DEPTH_TEST),cull=GL11.glIsEnabled(GL11.GL_CULL_FACE),scissored=GL11.glIsEnabled(GL11.GL_SCISSOR_TEST),depthMask=GL11.glGetBoolean(GL11.GL_DEPTH_WRITEMASK);
  final int depthFunc=GL11.glGetInteger(GL11.GL_DEPTH_FUNC),src=GL11.glGetInteger(GL14.GL_BLEND_SRC_RGB),dst=GL11.glGetInteger(GL14.GL_BLEND_DST_RGB),srcA=GL11.glGetInteger(GL14.GL_BLEND_SRC_ALPHA),dstA=GL11.glGetInteger(GL14.GL_BLEND_DST_ALPHA);
  final int pack=GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING),alignment=GL11.glGetInteger(GL11.GL_PACK_ALIGNMENT),row=GL11.glGetInteger(GL11.GL_PACK_ROW_LENGTH),skipRows=GL11.glGetInteger(GL11.GL_PACK_SKIP_ROWS),skipPixels=GL11.glGetInteger(GL11.GL_PACK_SKIP_PIXELS);
  State(){GL11.glGetIntegerv(GL11.GL_VIEWPORT,viewport);GL11.glGetIntegerv(GL11.GL_SCISSOR_BOX,scissor);GL11.glGetFloatv(GL11.GL_COLOR_CLEAR_VALUE,clear);for(int i=0;i<12;i++){textures[i]=RenderSystem.getShaderTexture(i);RenderSystem.activeTexture(GL13.GL_TEXTURE0+i);bindings[i]=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);}RenderSystem.activeTexture(active);}
  public void close(){
   GL30.glBindFramebuffer(GL30.GL_DRAW_FRAMEBUFFER,draw);GL30.glBindFramebuffer(GL30.GL_READ_FRAMEBUFFER,read);RenderSystem.viewport(viewport[0],viewport[1],viewport[2],viewport[3]);
   RenderSystem.setProjectionMatrix(projection,sorter);RenderSystem.setTextureMatrix(texture);RenderSystem.setShader(()->shader);GL20.glUseProgram(program);RenderSystem.setShaderColor(color[0],color[1],color[2],color[3]);RenderSystem.clearColor(clear[0],clear[1],clear[2],clear[3]);
   if(blend)RenderSystem.enableBlend();else RenderSystem.disableBlend();RenderSystem.blendFuncSeparate(src,dst,srcA,dstA);if(depth)RenderSystem.enableDepthTest();else RenderSystem.disableDepthTest();RenderSystem.depthMask(depthMask);RenderSystem.depthFunc(depthFunc);if(cull)RenderSystem.enableCull();else RenderSystem.disableCull();if(scissored)RenderSystem.enableScissor(scissor[0],scissor[1],scissor[2],scissor[3]);else RenderSystem.disableScissor();
   for(int i=0;i<12;i++){RenderSystem.setShaderTexture(i,textures[i]);RenderSystem.activeTexture(GL13.GL_TEXTURE0+i);RenderSystem.bindTexture(bindings[i]);}RenderSystem.activeTexture(active);
   GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,pack);GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT,alignment);GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,row);GL11.glPixelStorei(GL11.GL_PACK_SKIP_ROWS,skipRows);GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,skipPixels);
  }
 }
}
