package space.pocketmate.estates;
import java.util.*;
import net.minecraft.item.*;

public final class ShopInventory {
 private ShopInventory(){}
 public static List<ItemStack> copy(List<ItemStack> items){return items.stream().map(ItemStack::copy).toList();}
 public static boolean plain(ItemStack stack,Item item){return !stack.isEmpty()&&ItemStack.areItemsAndComponentsEqual(stack,new ItemStack(item));}
 public static int count(List<ItemStack> slots,Item item){return slots.stream().filter(s->plain(s,item)).mapToInt(ItemStack::getCount).sum();}
 /** Empty slots plus compatible partial stacks, without overwriting existing items. */
 public static int capacity(List<ItemStack> slots,Item item){
  int total=0,max=new ItemStack(item).getMaxCount();
  for(ItemStack stack:slots)if(stack.isEmpty())total+=max;else if(plain(stack,item))total+=Math.max(0,stack.getMaxCount()-stack.getCount());
  return Math.min(2304,total);
 }
 public static int maxBuy(List<ItemStack> slots,Item item,long balance,long unitPrice){if(balance<0||unitPrice<1)throw new IllegalArgumentException();return (int)Math.min(capacity(slots,item),balance/unitPrice);}
 /** Work on copies: capacity/ownership failures leave the real inventory untouched. */
 public static List<ItemStack> plan(List<ItemStack> slots,Item item,int amount,boolean buy){
  if(amount<1||amount>2304)throw new IllegalArgumentException("수량은 1~2,304개로 입력해주세요.");
  List<ItemStack> result=new ArrayList<>(copy(slots));int remaining=amount;
  if(buy){
   for(ItemStack stack:result)if(plain(stack,item)){int n=Math.min(remaining,Math.max(0,stack.getMaxCount()-stack.getCount()));stack.increment(n);remaining-=n;}
   for(int i=0;i<result.size()&&remaining>0;i++)if(result.get(i).isEmpty()){ItemStack stack=new ItemStack(item);int n=Math.min(remaining,stack.getMaxCount());stack.setCount(n);result.set(i,stack);remaining-=n;}
   if(remaining>0)throw new IllegalArgumentException("인벤토리의 빈 공간이 부족합니다.");
  }else{
   if(count(slots,item)<amount)throw new IllegalArgumentException("판매할 일반 아이템 수량이 부족합니다. 이름·인챈트 등 추가 정보가 있는 아이템은 판매하지 않습니다.");
   for(ItemStack stack:result)if(plain(stack,item)){int n=Math.min(remaining,stack.getCount());stack.decrement(n);remaining-=n;}
  }
  return result;
 }
}
