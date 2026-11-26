package space.pocketmate.estates;
import java.util.*;
import net.minecraft.item.*;

public final class ShopInventory {
 private ShopInventory(){}
 public static List<ItemStack> copy(List<ItemStack> items){return items.stream().map(ItemStack::copy).toList();}
 public static boolean plain(ItemStack stack,Item item){return plain(stack,new ItemStack(item));}
 private static boolean plain(ItemStack stack,ItemStack template){return !stack.isEmpty()&&ItemStack.areItemsAndComponentsEqual(stack,template);}
 public static int count(List<ItemStack> slots,Item item){return count(slots,new ItemStack(item));}
 public static int count(List<ItemStack> slots,ItemStack template){return slots.stream().filter(s->plain(s,template)).mapToInt(ItemStack::getCount).sum();}
 /** Empty slots plus compatible partial stacks, without overwriting existing items. */
 public static int capacity(List<ItemStack> slots,Item item){return capacity(slots,new ItemStack(item));}
 public static int capacity(List<ItemStack> slots,ItemStack template){
  int total=0,max=template.getMaxCount();
  for(ItemStack stack:slots)if(stack.isEmpty())total+=max;else if(plain(stack,template))total+=Math.max(0,stack.getMaxCount()-stack.getCount());
  return Math.min(2304,total);
 }
 public static int maxBuy(List<ItemStack> slots,Item item,long balance,long unitPrice){return maxBuy(slots,new ItemStack(item),balance,unitPrice);}
 public static int maxBuy(List<ItemStack> slots,ItemStack template,long balance,long unitPrice){if(balance<0||unitPrice<1)throw new IllegalArgumentException();return (int)Math.min(capacity(slots,template),balance/unitPrice);}
 /** Work on copies: capacity/ownership failures leave the real inventory untouched. */
 public static List<ItemStack> plan(List<ItemStack> slots,Item item,int amount,boolean buy){return plan(slots,new ItemStack(item),amount,buy);}
 public static List<ItemStack> plan(List<ItemStack> slots,ItemStack template,int amount,boolean buy){
  if(amount<1||amount>2304)throw new IllegalArgumentException("수량은 1~2,304개로 입력해주세요.");
  List<ItemStack> result=new ArrayList<>(copy(slots));int remaining=amount;
  if(buy){
   for(ItemStack stack:result)if(plain(stack,template)){int n=Math.min(remaining,Math.max(0,stack.getMaxCount()-stack.getCount()));stack.increment(n);remaining-=n;}
   for(int i=0;i<result.size()&&remaining>0;i++)if(result.get(i).isEmpty()){ItemStack stack=template.copy();int n=Math.min(remaining,stack.getMaxCount());stack.setCount(n);result.set(i,stack);remaining-=n;}
   if(remaining>0)throw new IllegalArgumentException("인벤토리의 빈 공간이 부족합니다.");
  }else{
   if(count(slots,template)<amount)throw new IllegalArgumentException("판매할 일반 아이템 수량이 부족합니다. 이름·인챈트 등 추가 정보가 있는 아이템은 판매하지 않습니다.");
   for(ItemStack stack:result)if(plain(stack,template)){int n=Math.min(remaining,stack.getCount());stack.decrement(n);remaining-=n;}
  }
  return result;
 }
}
