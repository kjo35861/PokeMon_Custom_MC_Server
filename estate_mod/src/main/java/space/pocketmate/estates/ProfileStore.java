package space.pocketmate.estates;

import com.google.gson.*;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.*;

/** Cosmetic ownership and equipment belong to the server, independently of estates. */
public final class ProfileStore {
    public record Cosmetic(String kind,String id,String name,String image,boolean starter,String color,String lightColor,String glyph,String font) {
        public Cosmetic(String kind,String id,String name,String image,boolean starter) {
            this(kind,id,name,image,starter,"#ffe0a0","#896000","\uE001","pocketmate:titles");
        }
    }
    public static final List<Cosmetic> CATALOG=buildCatalog();
    private static List<Cosmetic> buildCatalog(){
        List<Cosmetic> items=new ArrayList<>(List.of(
        new Cosmetic("icon","skin","내 스킨 얼굴","",true),
        new Cosmetic("icon","bulbasaur","이상해씨","./profile-assets/bulbasaur.png",true),
        new Cosmetic("icon","charmander","파이리","./profile-assets/charmander.png",true),
        new Cosmetic("icon","squirtle","꼬부기","./profile-assets/squirtle.png",true),
        new Cosmetic("icon","pikachu","피카츄","./profile-assets/pikachu.png",false),
        new Cosmetic("icon","eevee","이브이","./profile-assets/eevee.png",false),
        new Cosmetic("title","none","칭호 없음","",true),
        new Cosmetic("title","beginner","새로운 모험가","",true),
        new Cosmetic("title","companion","함께 걷는 친구","",false),
        new Cosmetic("banner","none","기본 카드","",true),
        new Cosmetic("banner","forest","초록빛 숲길","./profile-assets/forest.svg",true),
        new Cosmetic("banner","night","별빛 야영","./profile-assets/night.svg",true),
        new Cosmetic("banner","sky","하늘 항로","./profile-assets/sky.svg",false)
    ));
        items.addAll(LegendaryTitles.entries());return List.copyOf(items);
    }
    public record Profile(String icon,String title,String banner,Set<String> owned) {
        public Profile { owned=Set.copyOf(owned); }
    }
    /** Public equipment only: never disclose ownership or create a record during a lookup. */
    public record Appearance(String icon,String iconImage,String banner,String bannerImage) {}
    public String equippedTitle(UUID id) { return profiles.getOrDefault(id,starter()).title(); }
    public Appearance appearance(UUID id) {
        Profile profile=profiles.getOrDefault(id,starter());
        return new Appearance(profile.icon,cosmetic("icon",profile.icon).image,profile.banner,cosmetic("banner",profile.banner).image);
    }
    public static final class Denied extends Exception { public Denied(String message){super(message);} }
    private final Path path;
    private final Map<UUID,Profile> profiles=new LinkedHashMap<>();
    private static final Gson JSON=new GsonBuilder().setPrettyPrinting().create();
    public ProfileStore(Path path) throws IOException {
        this.path=path;
        if(!Files.exists(path))return;
        try {
            JsonObject root=JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            if(root.get("formatVersion").getAsInt()!=1)throw new IllegalArgumentException();
            JsonObject entries=root.getAsJsonObject("profiles");
            for(var entry:entries.entrySet()) {
                UUID id=UUID.fromString(entry.getKey());JsonObject value=entry.getValue().getAsJsonObject();
                Set<String> owned=new HashSet<>();for(JsonElement item:value.getAsJsonArray("owned")) {
                    String key=item.getAsString();if(CATALOG.stream().noneMatch(c->key.equals(c.kind+":"+c.id))||!owned.add(key))throw new IllegalArgumentException();
                }
                Profile profile=new Profile(value.get("icon").getAsString(),value.get("title").getAsString(),value.get("banner").getAsString(),owned);
                validate(profile,"icon",profile.icon);validate(profile,"title",profile.title);validate(profile,"banner",profile.banner);
                profiles.put(id,profile);
            }
        }catch(Exception invalid){throw new IOException("Invalid profile store; refusing to reset cosmetic ownership",invalid);}
    }
    public static Cosmetic cosmetic(String kind,String id){return CATALOG.stream().filter(c->c.kind.equals(kind)&&c.id.equals(id)).findFirst().orElse(null);}
    private static Profile starter(){
        Set<String> owned=new HashSet<>();for(Cosmetic c:CATALOG)if(c.starter)owned.add(c.kind+":"+c.id);
        return new Profile("skin","beginner","none",owned);
    }
    public Profile get(UUID id) throws IOException {
        Profile profile=profiles.get(id);if(profile!=null)return profile;
        profile=starter();commit(id,profile);return profile;
    }
    private static void validate(Profile profile,String kind,String id) throws Denied {
        if(cosmetic(kind,id)==null||!profile.owned.contains(kind+":"+id))throw new Denied("보유한 꾸미기 항목만 착용할 수 있습니다.");
    }
    public Profile equip(UUID id,String icon,String title,String banner) throws IOException,Denied {
        Profile current=get(id);validate(current,"icon",icon);validate(current,"title",title);validate(current,"banner",banner);
        Profile next=new Profile(icon,title,banner,current.owned);commit(id,next);return next;
    }
    public void grant(UUID id,String kind,String item) throws IOException,Denied {
        if(cosmetic(kind,item)==null)throw new Denied("존재하지 않는 꾸미기 항목입니다.");
        Profile current=get(id);Set<String> owned=new HashSet<>(current.owned);if(!owned.add(kind+":"+item))return;
        commit(id,new Profile(current.icon,current.title,current.banner,owned));
    }
    private void commit(UUID id,Profile profile) throws IOException {
        Map<UUID,Profile> next=new LinkedHashMap<>(profiles);next.put(id,profile);
        JsonObject root=new JsonObject(),entries=new JsonObject();root.addProperty("formatVersion",1);
        next.forEach((uuid,value)->entries.add(uuid.toString(),JSON.toJsonTree(value)));root.add("profiles",entries);
        Files.createDirectories(path.getParent());Path temporary=Files.createTempFile(path.getParent(),"profiles-",".tmp");
        try {
            byte[] bytes=JSON.toJson(root).getBytes(java.nio.charset.StandardCharsets.UTF_8);
            try(FileChannel file=FileChannel.open(temporary,StandardOpenOption.WRITE)){ByteBuffer buffer=ByteBuffer.wrap(bytes);while(buffer.hasRemaining())file.write(buffer);file.force(true);}
            if(Files.exists(path))Files.copy(path,path.resolveSibling(path.getFileName()+".bak"),StandardCopyOption.REPLACE_EXISTING);
            try{Files.move(temporary,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}
            catch(AtomicMoveNotSupportedException ignored){Files.move(temporary,path,StandardCopyOption.REPLACE_EXISTING);}
            profiles.clear();profiles.putAll(next);
        }finally{Files.deleteIfExists(temporary);}
    }
}
