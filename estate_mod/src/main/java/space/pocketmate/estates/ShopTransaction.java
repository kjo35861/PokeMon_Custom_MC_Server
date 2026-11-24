package space.pocketmate.estates;
/** Normal-operation atomicity: failed wallet persistence restores the pre-trade inventory. */
public final class ShopTransaction {
 private ShopTransaction(){}
 @FunctionalInterface public interface Payment {void save() throws Exception;}
 public static void commit(Runnable applyInventory,Runnable restoreInventory,Payment payment) throws Exception {
  applyInventory.run();
  try{payment.save();}catch(Exception error){restoreInventory.run();throw error;}
 }
}
