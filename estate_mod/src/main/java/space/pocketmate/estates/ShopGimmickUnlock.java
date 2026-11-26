package space.pocketmate.estates;

import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.server.network.ServerPlayerEntity;

/** Pixelmon shares its Mega equipment entitlement with Z-Moves. */
enum ShopGimmickUnlock {
 MEGA("canMega","unlockMega"), DYNAMAX("canDynamax","unlockDynamax"), TERA("canTerastallize","unlockTerastal");
 static final String TERA_ORB="pocketmate:tera_orb";
 static final String DYNAMAX_BAND="pocketmate:dynamax_band";
 static boolean isVirtual(String id){return TERA_ORB.equals(id)||DYNAMAX_BAND.equals(id);}
 private final String predicate, unlock;
 ShopGimmickUnlock(String predicate,String unlock){this.predicate=predicate;this.unlock=unlock;}
 static ShopGimmickUnlock forItem(String id){
  return switch(id){case "pixelmon:z_ring","pixelmon:key_stone" -> MEGA;case TERA_ORB -> TERA;case DYNAMAX_BAND -> DYNAMAX;default -> null;};
 }
 static boolean available(){return FabricLoader.getInstance().isModLoaded("pixelmon");}
 boolean owned(ServerPlayerEntity player) {
  return Boolean.TRUE.equals(call(call(party(player),"getMegaItemsUnlocked"),predicate));
 }
 void grant(ServerPlayerEntity player) {
  Object party=party(player);
  invoke(party,unlock,new Class<?>[]{boolean.class},true);
 }
 static Runnable restorePoint(ServerPlayerEntity player){
  Object party=party(player), flags=call(party,"getMegaItemsUnlocked"), equipped=call(party,"getMegaItem");
  return ()->{
   invoke(party,"setMegaItemsUnlocked",new Class<?>[]{flags.getClass()},flags);
   if(equipped!=null)invoke(party,"setMegaItem",new Class<?>[]{equipped.getClass(),boolean.class},equipped,true);
  };
 }
 private static Object party(ServerPlayerEntity player) {
  try {
   return Class.forName("com.pixelmonmod.pixelmon.api.storage.StorageProxy")
       .getMethod("getPartyNow",PlayerEntity.class).invoke(null,player);
  } catch(ReflectiveOperationException error){throw unavailable(error);}
 }
 private static Object call(Object target,String name) {
  if(target==null)throw unavailable(null);
  return invoke(target,name,new Class<?>[0]);
 }
 private static Object invoke(Object target,String name,Class<?>[] types,Object... args) {
  try{return target.getClass().getMethod(name,types).invoke(target,args);}
  catch(ReflectiveOperationException error){throw unavailable(error);}
 }
 private static IllegalStateException unavailable(Throwable cause){return new IllegalStateException("Pixelmon 기믹 해금을 처리하지 못했습니다.",cause);}
}
