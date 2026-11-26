package space.pocketmate.estates;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.item.ItemStack;
import net.minecraft.registry.Registries;
import net.minecraft.util.Identifier;

final class ShopPixelmonItems {
 private static Map<String,ItemStack> balls=Map.of();
 private static Map<String,String> categories=Map.of();

 private ShopPixelmonItems(){}

 static void load() throws ReflectiveOperationException {
  balls=Map.of();
  categories=Map.of();
  if(!ShopGimmickUnlock.available())return;
  var ballStacks=new LinkedHashMap<String,ItemStack>();
  var defaults=new LinkedHashMap<String,String>();
  var registry=Class.forName("com.pixelmonmod.pixelmon.api.pokemon.item.pokeball.PokeBallRegistry");
  var ballType=Class.forName("com.pixelmonmod.pixelmon.api.pokemon.item.pokeball.PokeBall");
  var getName=ballType.getMethod("getName");
  var getStack=ballType.getMethod("getBallItem");
  for(Object ball:(List<?>)registry.getMethod("getAll").invoke(null)){
   String name=(String)getName.invoke(ball);
   Identifier id=Identifier.tryParse(name.contains(":")?name:"pixelmon:"+name);
   if(id==null)continue;
   ItemStack stack=(ItemStack)getStack.invoke(ball);
   if(!stack.isEmpty()){
    ballStacks.put(id.toString(),stack.copy());
    defaults.put(id.toString(),"balls");
   }
  }
  var crystal=Class.forName("com.pixelmonmod.pixelmon.items.heldItems.ZCrystalItem");
  var mega=Class.forName("com.pixelmonmod.pixelmon.items.heldItems.MegaStoneItem");
  var held=Class.forName("com.pixelmonmod.pixelmon.items.HeldItem");
  for(var item:Registries.ITEM){
   var id=Registries.ITEM.getId(item);
   if(!id.getNamespace().equals("pixelmon"))continue;
   String category=crystal.isInstance(item)?"zcrystals":mega.isInstance(item)?"megastones":held.isInstance(item)?"held":null;
   if(category!=null)defaults.put(id.toString(),category);
  }
  balls=Map.copyOf(ballStacks);
  categories=Map.copyOf(defaults);
 }

 static boolean isBall(String id){return balls.containsKey(id);}
 static ItemStack stack(String id){
  var ball=balls.get(id);
  return ball==null?new ItemStack(Registries.ITEM.get(Identifier.of(id))):ball.copy();
 }
 static Map<String,String> categories(){return categories;}
 static String ballNameKey(String id){
  Identifier key=Identifier.of(id);
  return "item."+key.getNamespace()+"."+key.getPath();
 }
}
