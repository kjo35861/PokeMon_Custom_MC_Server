package space.pocketmate.estates;

import com.google.gson.*;
import java.nio.file.*;
import java.io.IOException;
import java.util.*;
import net.minecraft.registry.Registries;
import net.minecraft.item.Items;
import net.minecraft.util.Identifier;

/** Revision-checked atomic configuration writes, with a retained previous-file backup. */
public final class ShopAdminStore {
 public record Rule(String id,String category,boolean buy,boolean sell,long buyPrice,long sellPrice) {
  public Rule {
   Identifier key=Identifier.tryParse(id);if(key==null||!id.equals(key.toString())||!Registries.ITEM.containsId(key)||Registries.ITEM.get(key)==Items.AIR)throw new IllegalArgumentException("존재하는 아이템 ID를 입력해주세요.");
   if(!ShopCatalog.CATEGORIES.contains(category)||buyPrice<1||buyPrice>1_000_000||sellPrice<1||sellPrice>=buyPrice)throw new IllegalArgumentException("분류와 가격을 확인해주세요. 판매가는 구매가보다 작아야 합니다.");
   if(buy&&ShopCatalog.forbiddenBuy(id))throw new IllegalArgumentException("운영용/압축 블록 등 구매 제외 품목은 등록할 수 없습니다.");
   var base=ShopCatalog.entries().get(id);
   if(sell&&(base==null||!base.sell()))throw new IllegalArgumentException("판매는 기존 광물·농작물 허용 품목으로 제한됩니다.");
   if(buy&&category.equals("minerals")&&(base==null||!base.category().equals("minerals")))throw new IllegalArgumentException("광물에는 미제련 광물만 등록할 수 있습니다.");
  }
 }
 public record Audit(long at,String actor,String action,String item,String summary) {}
 public record State(int schema,long revision,ShopPrices prices,Map<String,Rule> overrides,boolean buyPaused,boolean sellPaused,boolean estatePurchasesPaused,boolean missionRewardsPaused,String maintenanceReason,List<Audit> audit,Set<String> deleted) {
  public State {
   if(schema!=1||revision<0||revision>1_000_000_000_000L||prices==null)throw new IllegalArgumentException("상점 설정 버전을 확인해주세요.");
   deleted=Set.copyOf(deleted==null?Set.of():deleted);
   overrides=Map.copyOf(overrides==null?Map.of():overrides);audit=List.copyOf(audit==null?List.of():audit);
   maintenanceReason=maintenanceReason==null?"":maintenanceReason.strip();if(maintenanceReason.length()>120||audit.size()>100)throw new IllegalArgumentException("운영 안내 또는 기록 길이를 확인해주세요.");
   for(var e:overrides.entrySet())if(!e.getKey().equals(e.getValue().id()))throw new IllegalArgumentException("품목 설정 ID가 일치하지 않습니다.");
  }
 }
 private static final Gson JSON=new GsonBuilder().setPrettyPrinting().create();
 private final Path file;private State state;
 public ShopAdminStore(Path file) throws IOException {
  this.file=file;
  try{
   if(Files.exists(file)){
    JsonObject json=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
    state=json.has("schema")?JSON.fromJson(json,State.class):new State(1,0,JSON.fromJson(json,ShopPrices.class),Map.of(),false,false,false,false,"",List.of(),Set.of());
   }else{state=new State(1,0,ShopPrices.defaults(),Map.of(),false,false,false,false,"",List.of(),Set.of());persist(state);}
   effectivePrices(state);
  }catch(Exception e){throw new IOException("상점 설정을 읽지 못했습니다. 파일을 초기화하지 않았습니다.",e);}
 }
 public static void require(int level){if(level<2)throw new SecurityException("관리자 페이지는 OP 권한 레벨 2 이상만 사용할 수 있습니다.");}
 public synchronized State view(int level){require(level);return state;}
 public synchronized long revision(){return state.revision();}
 public synchronized ShopPrices prices(){return effectivePrices(state);}
 public synchronized String version(long now){return state.revision()+":"+prices().version(now);}
 public synchronized boolean paused(boolean buy){return buy?state.buyPaused():state.sellPaused();}
 public synchronized boolean estatePaused(){return state.estatePurchasesPaused();}
 public synchronized boolean missionsPaused(){return state.missionRewardsPaused();}
 public synchronized String reason(){return state.maintenanceReason();}
 private static ShopPrices effectivePrices(State value){
  Map<String,Long> buy=new HashMap<>(value.prices().buyPrices()),sell=new HashMap<>(value.prices().sellPrices());
  for(Rule r:value.overrides().values()){buy.put(r.id(),r.buyPrice());sell.put(r.id(),r.sellPrice());}
  var p=value.prices();return new ShopPrices(p.buyBase(),p.sellBase(),p.randomEnabled(),p.intervalSeconds(),p.deviationPercent(),p.seed(),buy,sell);
 }
 public synchronized Map<String,ShopCatalog.Entry> entries(){
  Map<String,ShopCatalog.Entry> result=new TreeMap<>(ShopCatalog.entries());
  for(Rule r:state.overrides().values())result.put(r.id(),new ShopCatalog.Entry(r.id(),r.category(),r.buy(),r.sell()));
  result.keySet().removeAll(state.deleted());
  return Collections.unmodifiableMap(result);
 }
 public synchronized Rule rule(String id){
  if(state.deleted().contains(id))throw new IllegalArgumentException("등록된 품목을 선택해주세요.");
  if(state.overrides().containsKey(id))return state.overrides().get(id);
  var e=ShopCatalog.entries().get(id);if(e==null)throw new IllegalArgumentException("등록된 품목을 선택해주세요.");
  var p=prices();return new Rule(e.id(),e.category(),e.buy(),e.sell(),p.buy(e.id(),0),p.sellBaseFor(e.id()));
 }
 public synchronized void upsert(int level,long expected,Rule rule,String actor) throws IOException {
  require(level);check(expected);Map<String,Rule> next=new HashMap<>(state.overrides());next.put(rule.id(),rule);
  var old=entries().get(rule.id());String summary=(old==null?"추가":"수정")+" · 구매 "+(rule.buy()?rule.buyPrice()+"원":"제외")+" / 판매 "+(rule.sell()?rule.sellPrice()+"원":"제외");
  var deleted=new HashSet<>(state.deleted());deleted.remove(rule.id());
  save(deleted,next,state.prices(),state.buyPaused(),state.sellPaused(),state.estatePurchasesPaused(),state.missionRewardsPaused(),state.maintenanceReason(),actor,"품목 변경",rule.id(),summary);
 }
 public synchronized void disable(int level,long expected,String id,String side,String actor) throws IOException {
  require(level);check(expected);Rule old=rule(id);if(!Set.of("buy","sell","both").contains(side))throw new IllegalArgumentException("구매/판매 구분을 확인해주세요.");
  Map<String,Rule> next=new HashMap<>(state.overrides());next.put(id,new Rule(id,old.category(),old.buy()&&!Set.of("buy","both").contains(side),old.sell()&&!Set.of("sell","both").contains(side),old.buyPrice(),old.sellPrice()));
  save(state.deleted(),next,state.prices(),state.buyPaused(),state.sellPaused(),state.estatePurchasesPaused(),state.missionRewardsPaused(),state.maintenanceReason(),actor,"일시정지",id,side+" 거래 일시정지");
 }
 public synchronized void delete(int level,long expected,String id,String actor) throws IOException {
  require(level);check(expected);rule(id);
  var next=new HashMap<>(state.overrides());next.remove(id);
  var deleted=new HashSet<>(state.deleted());
  if(ShopCatalog.entries().containsKey(id))deleted.add(id);
  save(deleted,next,state.prices(),state.buyPaused(),state.sellPaused(),state.estatePurchasesPaused(),
      state.missionRewardsPaused(),state.maintenanceReason(),actor,"품목 삭제",id,"상점 목록에서 삭제");
 }
 public synchronized void configure(int level,long expected,ShopPrices prices,boolean buyPaused,boolean sellPaused,boolean estatePaused,boolean missionPaused,String reason,String actor) throws IOException {
  require(level);check(expected);save(state.deleted(),state.overrides(),prices,buyPaused,sellPaused,estatePaused,missionPaused,reason,actor,"가격·점검 설정","", "기본 구매 "+prices.buyBase()+"원 / 판매 "+prices.sellBase()+"원 · 변동 "+prices.randomEnabled()+" · 구매 중지 "+buyPaused+" / 판매 중지 "+sellPaused+" · 영지 중지 "+estatePaused+" / 임무 보상 중지 "+missionPaused);
 }
 private void check(long expected){if(expected!=state.revision())throw new IllegalArgumentException("다른 관리자가 설정을 변경했습니다. 새로고침 후 다시 수정해주세요.");}
 private void save(Set<String> deleted,Map<String,Rule> rules,ShopPrices prices,boolean bp,boolean sp,boolean ep,boolean mp,String reason,String actor,String action,String item,String summary) throws IOException {
  List<Audit> log=new ArrayList<>(state.audit());log.add(new Audit(System.currentTimeMillis(),actor,action,item,summary));if(log.size()>100)log=log.subList(log.size()-100,log.size());
  State next=new State(1,state.revision()+1,prices,rules,bp,sp,ep,mp,reason,log,deleted);effectivePrices(next);persist(next);state=next;
 }
 private void persist(State value) throws IOException {
  Path parent=file.toAbsolutePath().getParent();Files.createDirectories(parent);Path temp=Files.createTempFile(parent,"shop-",".tmp");
  try{Files.writeString(temp,JSON.toJson(value));if(Files.exists(file))Files.copy(file,file.resolveSibling(file.getFileName()+".bak"),StandardCopyOption.REPLACE_EXISTING);
   try{Files.move(temp,file,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}catch(AtomicMoveNotSupportedException ignored){Files.move(temp,file,StandardCopyOption.REPLACE_EXISTING);}
  }finally{Files.deleteIfExists(temp);}
 }
}
