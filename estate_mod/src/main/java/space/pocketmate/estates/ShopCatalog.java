package space.pocketmate.estates;

import java.util.*;
import net.minecraft.block.Block;
import net.minecraft.item.*;
import net.minecraft.registry.Registries;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.EmptyBlockView;

/** Vanilla-only catalog. Never accept an arbitrary browser-supplied registry item. */
public final class ShopCatalog {
 public static final List<String> CATEGORIES=List.of("building","colored","decoration","minerals","crops","balls","held","zcrystals","megastones");
 private static final Set<String> MINERALS=Set.of("coal","raw_iron","raw_copper","raw_gold","diamond","emerald","lapis_lazuli","redstone","quartz","amethyst_shard","ancient_debris","flint","glowstone_dust");
 private static final Set<String> SEEDS=Set.of("wheat_seeds","beetroot_seeds","pumpkin_seeds","melon_seeds","torchflower_seeds","pitcher_pod","chorus_flower","carrot","potato","cocoa_beans","nether_wart","sweet_berries","glow_berries","sugar_cane","bamboo","cactus","kelp","brown_mushroom","red_mushroom");
 private static final Set<String> PRODUCE=Set.of("chorus_fruit","poisonous_potato","wheat","beetroot","carrot","potato","pumpkin","melon_slice","cocoa_beans","nether_wart","sweet_berries","glow_berries","sugar_cane","bamboo","cactus","kelp","brown_mushroom","red_mushroom","torchflower","pitcher_plant");
 private static final Set<String> EXCLUDED=Set.of("air","bedrock","barrier","structure_void","structure_block","jigsaw","command_block","chain_command_block","repeating_command_block","light","spawner","trial_spawner","vault","reinforced_deepslate","budding_amethyst","infested_stone","infested_cobblestone","infested_stone_bricks","infested_mossy_stone_bricks","infested_cracked_stone_bricks","infested_chiseled_stone_bricks","infested_deepslate","coal_block","raw_iron_block","raw_copper_block","raw_gold_block","iron_block","copper_block","gold_block","diamond_block","emerald_block","lapis_block","redstone_block","netherite_block","hay_block","melon","glowstone","bamboo_block","nether_wart_block");
 private static final String COLORS="white|orange|magenta|light_blue|yellow|lime|pink|gray|light_gray|cyan|purple|blue|brown|green|red|black";
 public record Entry(String id,String category,boolean buy,boolean sell) {public String saleCategory(){return sell?(category.equals("minerals")?"minerals":"crops"):"";}}
 private static final Map<String,String> NAMES=names();
 private static Map<String,String> names(){
  try(var in=ShopCatalog.class.getResourceAsStream("/pocketmate-shop-ko.json")){
   var json=com.google.gson.JsonParser.parseReader(new java.io.InputStreamReader(in,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
   Map<String,String> out=new HashMap<>();json.entrySet().forEach(e->out.put(e.getKey(),e.getValue().getAsString()));return Map.copyOf(out);
  }catch(Exception ignored){return Map.of();}
 }
 public static String name(Item item){return NAMES.getOrDefault(item.getTranslationKey(),item.getName().getString());}
 private static Map<String,Entry> catalog;
 public static synchronized Map<String,Entry> entries(){
  if(catalog!=null)return catalog;
  Map<String,Entry> out=new TreeMap<>();
  for(Item item:Registries.ITEM){
   var id=Registries.ITEM.getId(item);if(!id.getNamespace().equals("minecraft"))continue;
   String name=id.getPath();boolean mineral=MINERALS.contains(name),crop=PRODUCE.contains(name)||SEEDS.contains(name);
   String category=null;boolean buy=true;
   if(mineral)category="minerals";
   else if(Set.of("torchflower","pitcher_plant").contains(name))category="decoration";
   else if(SEEDS.contains(name)||crop){category="crops";buy=SEEDS.contains(name);}
   else if(item instanceof BlockItem blockItem){
    if(EXCLUDED.contains(name)||name.endsWith("_ore")||name.endsWith("_slab")||name.endsWith("_stairs"))continue;
    if(name.matches("("+COLORS+")_(wool|carpet|terracotta|glazed_terracotta|concrete|concrete_powder|stained_glass|stained_glass_pane|shulker_box|candle|banner|bed)")||Set.of("glass","glass_pane","terracotta","shulker_box","candle").contains(name))category="colored";
    else {
     boolean cube;
     try{cube=Block.isShapeFullCube(blockItem.getBlock().getDefaultState().getOutlineShape(EmptyBlockView.INSTANCE,BlockPos.ORIGIN));}catch(RuntimeException ignored){cube=false;}
     category=cube?"building":"decoration";
    }
   }
   if(category!=null)out.put(id.toString(),new Entry(id.toString(),category,buy,mineral||crop));
  }
  catalog=Collections.unmodifiableMap(out);return catalog;
 }
 public static Entry require(String id){Entry e=entries().get(id);if(e==null)throw new IllegalArgumentException("상점에 등록되지 않은 아이템입니다.");return e;}
}
