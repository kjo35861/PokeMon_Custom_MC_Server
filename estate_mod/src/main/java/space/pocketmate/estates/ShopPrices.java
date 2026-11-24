package space.pocketmate.estates;
import java.util.SplittableRandom;
import java.util.Map;
import java.util.HashSet;

/** Stable within a server-defined price window. Random pricing is off by default. */
public record ShopPrices(long buyBase,long sellBase,boolean randomEnabled,long intervalSeconds,int deviationPercent,long seed,Map<String,Long> buyPrices,Map<String,Long> sellPrices) {
 public ShopPrices(long buyBase,long sellBase,boolean randomEnabled,long intervalSeconds,int deviationPercent,long seed){this(buyBase,sellBase,randomEnabled,intervalSeconds,deviationPercent,seed,Map.of(),Map.of());}
 public ShopPrices{
  buyPrices=Map.copyOf(buyPrices==null?Map.of():buyPrices);sellPrices=Map.copyOf(sellPrices==null?Map.of():sellPrices);
  var ids=new HashSet<>(buyPrices.keySet());ids.addAll(sellPrices.keySet());
  for(String id:ids){long buy=buyPrices.getOrDefault(id,buyBase),sell=sellPrices.getOrDefault(id,sellBase);if(!id.matches("minecraft:[a-z0-9_]+")||buy<1||buy>1_000_000||sell<1||sell>=buy)throw new IllegalArgumentException("아이템별 가격 설정을 확인해주세요.");}
  if(buyBase<1||buyBase>1_000_000||sellBase<1||sellBase>=buyBase||intervalSeconds<60||intervalSeconds>604800||deviationPercent<0||deviationPercent>40)throw new IllegalArgumentException("상점 가격 설정이 올바르지 않습니다.");}
 public static ShopPrices defaults(){return new ShopPrices(100,50,false,3600,15,0x504f434b4554L);}
 public String version(long millis){String config=Integer.toUnsignedString(hashCode(),36);return randomEnabled?"window_"+config+"_"+Math.floorDiv(millis,intervalSeconds*1000):"fixed_"+config;}
 public long nextAt(long millis){return randomEnabled?(Math.floorDiv(millis,intervalSeconds*1000)+1)*intervalSeconds*1000:0;}
 public long buy(String id,long millis){return buyPrices.getOrDefault(id,buyBase);}
 public long sell(String id,long millis){long base=sellPrices.getOrDefault(id,sellBase);if(!randomEnabled)return base;long epoch=Math.floorDiv(millis,intervalSeconds*1000);int pct=new SplittableRandom(seed^id.hashCode()^epoch*0x9e3779b97f4a7c15L).nextInt(-deviationPercent,deviationPercent+1);return Math.min(buy(id,millis)-1,Math.max(1,base+Math.round(base*pct/100.0)));}
}
