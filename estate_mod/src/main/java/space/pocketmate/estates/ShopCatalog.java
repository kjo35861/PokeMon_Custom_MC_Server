package space.pocketmate.estates;

import java.util.*;
import net.minecraft.block.Block;
import net.minecraft.item.*;
import net.minecraft.registry.Registries;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.EmptyBlockView;

/** Vanilla-only catalog. Never accept an arbitrary browser-supplied registry item. */
public final class ShopCatalog {
 public static final List<String> CATEGORIES=List.of("building","colored","decoration","minerals","crops","balls","held","zcrystals","megastones","gimmicks");
 private static final Map<String,String> GIMMICK_NAMES=Map.of("pixelmon:key_stone","메가링 · Z링",ShopGimmickUnlock.TERA_ORB,"테라스탈오브",ShopGimmickUnlock.DYNAMAX_BAND,"다이맥스밴드");
 private static final Set<String> MINERALS=Set.of("coal","raw_iron","raw_copper","raw_gold","diamond","emerald","lapis_lazuli","redstone","quartz","amethyst_shard","ancient_debris","flint","glowstone_dust");
 private static final Set<String> SEEDS=Set.of("wheat_seeds","beetroot_seeds","pumpkin_seeds","melon_seeds","torchflower_seeds","pitcher_pod","chorus_flower","carrot","potato","cocoa_beans","nether_wart","sweet_berries","glow_berries","sugar_cane","bamboo","cactus","kelp","brown_mushroom","red_mushroom");
 private static final Set<String> PRODUCE=Set.of("chorus_fruit","poisonous_potato","wheat","beetroot","carrot","potato","pumpkin","melon_slice","cocoa_beans","nether_wart","sweet_berries","glow_berries","sugar_cane","bamboo","cactus","kelp","brown_mushroom","red_mushroom","torchflower","pitcher_plant");
 private static final Set<String> RESTRICTED_ITEMS=Set.of("air","bedrock","barrier","structure_void","structure_block","jigsaw","command_block","chain_command_block","repeating_command_block","light","spawner","trial_spawner","vault","reinforced_deepslate","budding_amethyst","infested_stone","infested_cobblestone","infested_stone_bricks","infested_mossy_stone_bricks","infested_cracked_stone_bricks","infested_chiseled_stone_bricks","infested_deepslate");
 private static final Set<String> MANUAL_ITEMS=Set.of("coal_block","raw_iron_block","raw_copper_block","raw_gold_block","iron_block","copper_block","gold_block","diamond_block","emerald_block","lapis_block","redstone_block","netherite_block","hay_block","melon","glowstone","bamboo_block","nether_wart_block");
 private static final String COLORS="white|orange|magenta|light_blue|yellow|lime|pink|gray|light_gray|cyan|purple|blue|brown|green|red|black";
 public record Entry(String id,String category,boolean buy,boolean sell) {public String saleCategory(){return sell?category:"";}}
 private static final List<String> BLOCK_FAMILIES=List.of("log","wood","stem","hyphae","planks","wool","concrete","concrete_powder","terracotta","glazed_terracotta","stained_glass","stained_glass_pane","glass","froglight","lantern");
 private static final java.util.regex.Pattern COLOR_PREFIX=java.util.regex.Pattern.compile("^(?:"+COLORS+")_");
 static Comparator<Entry> categoryOrder(){
  return Comparator.comparingInt((Entry e)->CATEGORIES.indexOf(e.category()))
      .thenComparing(e->family(e.id())).thenComparing(Entry::id);
 }
 private static String family(String id){
  String path=id.substring(id.indexOf(':')+1);
  String uncolored=COLOR_PREFIX.matcher(path).replaceFirst("");
  if(!uncolored.equals(path))return uncolored;
  for(String type:BLOCK_FAMILIES)if(path.equals(type)||path.endsWith("_"+type))return type;
  for(String stone:List.of("deepslate","blackstone","sandstone","stone","quartz","copper","prismarine","tuff","basalt"))
   if(Arrays.asList(path.split("_")).contains(stone))return stone;
  return path;
 }
 private static final Map<String,String> NAMES=names();
 private static Map<String,String> pixelmonNames=Map.of();
 private static Map<String,String> pixelmonEnglish=Map.of();
 private static Map<String,String> names(){
  try(var in=ShopCatalog.class.getResourceAsStream("/pocketmate-shop-ko.json")){
   var json=com.google.gson.JsonParser.parseReader(new java.io.InputStreamReader(in,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
   Map<String,String> out=new HashMap<>();json.entrySet().forEach(e->out.put(e.getKey(),e.getValue().getAsString()));return Map.copyOf(out);
  }catch(Exception ignored){return Map.of();}
 }
 private static Map<String,String> modNames(String owner,String namespace){
  return modNames(owner,namespace,"ko_kr");
 }
 private static Map<String,String> modNames(String owner,String namespace,String language){
  try(var in=Class.forName(owner).getResourceAsStream("/assets/"+namespace+"/lang/"+language+".json")){
   if(in==null)return Map.of();
   var json=com.google.gson.JsonParser.parseReader(new java.io.InputStreamReader(in,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
   var names=new HashMap<String,String>();
   json.entrySet().stream().filter(e->e.getKey().startsWith("item."+namespace+".")||e.getKey().startsWith("block."+namespace+"."))
       .forEach(e->names.put(e.getKey(),e.getValue().getAsString()));
   return names;
  }catch(ClassNotFoundException absent){return Map.of();}
  catch(Exception error){
   org.slf4j.LoggerFactory.getLogger("pocketmate-shop").warn("Could not load item translations for {}",namespace,error);
   return Map.of();
  }
 }
 private static void loadModNames(){
  if(!ShopGimmickUnlock.available())return;
  var names=new HashMap<>(modNames("com.pixelmonmod.pixelmon.Pixelmon","pixelmon"));
  names.putAll(modNames(ShopCatalog.class.getName(),"pixelmon"));
  names.putAll(modNames("space.pocketmate.mega.PocketmateMegaBridge","pocketmate_mega"));
  pixelmonNames=Map.copyOf(names);
  pixelmonEnglish=modNames("com.pixelmonmod.pixelmon.Pixelmon","pixelmon","en_us");
 }
 static String description(Entry entry, ItemStack stack) {
  String id=entry.id();
  if(ShopGimmickUnlock.forItem(id)!=null){
   return switch(ShopGimmickUnlock.forItem(id)){
    case MEGA -> "메가진화와 Z기술을 사용할 수 있도록 계정에 해금합니다.";
    case DYNAMAX -> "다이맥스를 사용할 수 있도록 계정에 해금합니다.";
    case TERA -> "테라스탈을 사용할 수 있도록 계정에 해금합니다.";
   };
  }
  String key=(ShopPixelmonItems.isBall(id)?ShopPixelmonItems.ballNameKey(id):stack.getItem().getTranslationKey())+".tooltip";
  String tooltip=pixelmonNames.getOrDefault(key,pixelmonEnglish.getOrDefault(key,""));
  if(!tooltip.isBlank())return tooltip.replaceAll("§.","").strip();
  return switch(ShopPixelmonItems.categories().getOrDefault(id,entry.category())){
   case "building", "colored" -> "설치하여 건축에 사용할 수 있는 블록입니다.";
   case "decoration" -> "공간을 꾸미는 데 사용할 수 있는 아이템입니다.";
   case "minerals" -> "제작이나 가공에 사용할 수 있는 광물입니다.";
   case "crops" -> "재배나 농사에 사용할 수 있는 아이템입니다.";
   case "balls" -> "야생 포켓몬을 포획하는 데 사용합니다.";
   case "megastones" -> "호환되는 포켓몬에게 지니게 하면 해당 포켓몬의 메가진화에 사용할 수 있습니다.";
   case "zcrystals" -> "호환되는 포켓몬이 조건에 맞는 Z기술을 사용하는 데 필요합니다.";
   case "held" -> "포켓몬에게 지니게 할 수 있는 아이템입니다.";
   default -> "별도 아이템 설명이 없습니다.";
  };
 }
 public static String name(Item item){
  String key=item.getTranslationKey();
  String localized=pixelmonNames.get(key);
  return localized!=null?localized:NAMES.getOrDefault(key,item.getName().getString());
 }
 public static String name(String id){
  if(GIMMICK_NAMES.containsKey(id))return GIMMICK_NAMES.get(id);
  if(ShopPixelmonItems.isBall(id))return pixelmonNames.getOrDefault(ShopPixelmonItems.ballNameKey(id),id.substring(id.indexOf(':')+1));
  return name(Registries.ITEM.get(net.minecraft.util.Identifier.of(id)));
 }
 static Set<String> searchableIds(){
  Set<String> ids=new TreeSet<>(ShopPixelmonItems.categories().keySet());
  for(var item:Registries.ITEM)if(item!=Items.AIR)ids.add(Registries.ITEM.getId(item).toString());
  ids.addAll(entries().keySet());
  return ids;
 }
 static String suggestedCategory(String id){
  var base=entries().get(id);
  return base!=null?base.category():ShopPixelmonItems.categories().get(id);
 }
 private static Map<String,Entry> catalog;
 public static synchronized Map<String,Entry> entries(){
  if(catalog!=null)return catalog;
  loadModNames();
  Map<String,Entry> out=new TreeMap<>();
  for(Item item:Registries.ITEM){
   var id=Registries.ITEM.getId(item);if(!id.getNamespace().equals("minecraft"))continue;
   String name=id.getPath();boolean mineral=MINERALS.contains(name),crop=PRODUCE.contains(name)||SEEDS.contains(name);
   String category=null;boolean buy=true;
   if(mineral)category="minerals";
   else if(Set.of("torchflower","pitcher_plant").contains(name))category="decoration";
   else if(SEEDS.contains(name)||crop){category="crops";buy=SEEDS.contains(name);}
   else if(item instanceof BlockItem blockItem){
    if(RESTRICTED_ITEMS.contains(name)||MANUAL_ITEMS.contains(name)||name.endsWith("_ore")||name.endsWith("_slab")||name.endsWith("_stairs"))continue;
    if(name.matches("("+COLORS+")_(wool|carpet|terracotta|glazed_terracotta|concrete|concrete_powder|stained_glass|stained_glass_pane|shulker_box|candle|banner|bed)")||Set.of("glass","glass_pane","terracotta","shulker_box","candle").contains(name))category="colored";
    else {
     boolean cube;
     try{cube=Block.isShapeFullCube(blockItem.getBlock().getDefaultState().getOutlineShape(EmptyBlockView.INSTANCE,BlockPos.ORIGIN));}catch(RuntimeException ignored){cube=false;}
     category=cube?"building":"decoration";
    }
   }
   if(category!=null)out.put(id.toString(),new Entry(id.toString(),category,buy,mineral||crop));
  }
  for(String id:GIMMICK_NAMES.keySet()){
   if(ShopGimmickUnlock.isVirtual(id)?ShopGimmickUnlock.available():Registries.ITEM.containsId(net.minecraft.util.Identifier.of(id)))
    out.put(id,new Entry(id,"gimmicks",true,false));
  }
  catalog=Collections.unmodifiableMap(out);return catalog;
 }
 public static boolean forbiddenBuy(String id){var key=net.minecraft.util.Identifier.tryParse(id);return key==null||key.getPath().equals("air")||key.getNamespace().equals("minecraft")&&RESTRICTED_ITEMS.contains(key.getPath());}
 public static Entry require(String id){Entry e=entries().get(id);if(e==null)throw new IllegalArgumentException("상점에 등록되지 않은 아이템입니다.");return e;}
}
