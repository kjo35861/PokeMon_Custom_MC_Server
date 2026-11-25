package space.pocketmate.estates;

import com.google.gson.*;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.*;

/** Cosmetic ownership and equipment belong to the server, independently of estates. */
public final class ProfileStore {
    public record Cosmetic(String kind,String id,String name,String image,boolean starter,String color,String lightColor,String glyph,String font,String acquisitionCondition) {
        public Cosmetic(String kind,String id,String name,String image,boolean starter) {
            this(kind,id,name,image,starter,"#ffe0a0","#896000","\uE001","pocketmate:titles",kind.equals("title")?(id.equals("none")?"칭호를 표시하지 않는 기본 설정입니다.":starter?"서버 첫 접속 시 기본 지급됩니다.":"관리자가 지급하는 칭호입니다."):"");
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
    private Map<String,Cosmetic> titleOverrides=Map.of();
    private Set<String> deletedTitles=Set.of();
    public List<Cosmetic> catalog(){
        var result=new LinkedHashMap<String,Cosmetic>();
        for(Cosmetic item:CATALOG)
            if(!item.kind.equals("title")||!deletedTitles.contains(item.id))
                result.put(item.kind+":"+item.id,item);
        for(Cosmetic title:titleOverrides.values())result.put("title:"+title.id,title);
        return List.copyOf(result.values());
    }
    public void editTitle(String id,String name,String color,String icon,boolean create) throws IOException {
        if(!id.matches("[a-z0-9_-]{1,32}")||id.equals("none"))throw new IllegalArgumentException("칭호 ID는 영문 소문자·숫자·밑줄·하이픈 1~32자입니다.");
        name=name.strip();
        if(name.isEmpty()||name.length()>40||name.chars().anyMatch(Character::isISOControl)||!color.matches("#[0-9a-fA-F]{6}"))
            throw new IllegalArgumentException("칭호 이름과 #RRGGBB 색 코드를 확인해주세요.");
        Cosmetic old=cosmetic("title",id);
        if(create==(old!=null))throw new IllegalArgumentException(create?"이미 등록된 칭호 ID입니다.":"수정할 칭호가 없습니다.");
        if(!Set.of("keep","none","spark").contains(icon))throw new IllegalArgumentException("아이콘 설정을 확인해주세요.");
        Cosmetic source=old==null?new Cosmetic("title",id,name,"",false):old;
        boolean keep=icon.equals("keep");
        Cosmetic next=new Cosmetic("title",id,name,keep?source.image:"",source.starter,color,color,
            keep?source.glyph:icon.equals("none")?"":"",keep?source.font:"pocketmate:titles",source.acquisitionCondition);
        var overrides=new LinkedHashMap<>(titleOverrides);overrides.put(id,next);
        var deleted=new HashSet<>(deletedTitles);deleted.remove(id);
        persist(new LinkedHashMap<>(profiles),overrides,deleted);
    }
    public void deleteTitle(String id) throws IOException {
        if(id.equals("none")||cosmetic("title",id)==null)throw new IllegalArgumentException("삭제할 수 없는 칭호입니다.");
        var overrides=new LinkedHashMap<>(titleOverrides);overrides.remove(id);
        var deleted=new HashSet<>(deletedTitles);
        if(CATALOG.stream().anyMatch(c->c.kind.equals("title")&&c.id.equals(id)))deleted.add(id);
        var next=new LinkedHashMap<UUID,Profile>();
        profiles.forEach((uuid,profile)->{
            var owned=new HashSet<>(profile.owned);owned.remove("title:"+id);
            next.put(uuid,new Profile(profile.icon,profile.title.equals(id)?"none":profile.title,profile.banner,owned));
        });
        persist(next,overrides,deleted);
    }
    private final Map<UUID,Profile> profiles=new LinkedHashMap<>();
    private static final Gson JSON=new GsonBuilder().setPrettyPrinting().create();
    public ProfileStore(Path path) throws IOException {
        this.path=path;
        if(!Files.exists(path))return;
        try {
            JsonObject root=JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            if(root.get("formatVersion").getAsInt()!=1)throw new IllegalArgumentException();
            var loadedTitles=new LinkedHashMap<String,Cosmetic>();
            if(root.has("titleOverrides"))for(var entry:root.getAsJsonObject("titleOverrides").entrySet()){
                Cosmetic title=JSON.fromJson(entry.getValue(),Cosmetic.class);
                if(!entry.getKey().equals(title.id)||!title.kind.equals("title")||title.id.equals("none")||!title.color.matches("#[0-9a-fA-F]{6}"))throw new IllegalArgumentException();
                loadedTitles.put(title.id,title);
            }
            titleOverrides=Collections.unmodifiableMap(loadedTitles);
            var removed=new HashSet<String>();
            if(root.has("deletedTitles"))for(var value:root.getAsJsonArray("deletedTitles"))removed.add(value.getAsString());
            if(removed.contains("none"))throw new IllegalArgumentException();
            deletedTitles=Set.copyOf(removed);
            JsonObject entries=root.getAsJsonObject("profiles");
            for(var entry:entries.entrySet()) {
                UUID id=UUID.fromString(entry.getKey());JsonObject value=entry.getValue().getAsJsonObject();
                Set<String> owned=new HashSet<>();for(JsonElement item:value.getAsJsonArray("owned")) {
                    String key=item.getAsString();if(catalog().stream().noneMatch(c->key.equals(c.kind+":"+c.id))||!owned.add(key))throw new IllegalArgumentException();
                }
                Profile profile=new Profile(value.get("icon").getAsString(),value.get("title").getAsString(),value.get("banner").getAsString(),owned);
                validate(profile,"icon",profile.icon);validate(profile,"title",profile.title);validate(profile,"banner",profile.banner);
                profiles.put(id,profile);
            }
        }catch(Exception invalid){throw new IOException("Invalid profile store; refusing to reset cosmetic ownership",invalid);}
    }
    public Cosmetic cosmetic(String kind,String id){return catalog().stream().filter(c->c.kind.equals(kind)&&c.id.equals(id)).findFirst().orElse(null);}
    private Profile starter(){
        Set<String> owned=new HashSet<>();for(Cosmetic c:catalog())if(c.starter)owned.add(c.kind+":"+c.id);
        return new Profile("skin",owned.contains("title:beginner")?"beginner":"none","none",owned);
    }
    public Profile get(UUID id) throws IOException {
        Profile profile=profiles.get(id);if(profile!=null)return profile;
        profile=starter();commit(id,profile);return profile;
    }
    private void validate(Profile profile,String kind,String id) throws Denied {
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
    /** One persisted update; duplicate grants never alter equipment or other cosmetics. */
    public int grantAllTitles(UUID id) throws IOException {
        Profile current=get(id);Set<String> owned=new HashSet<>(current.owned);
        int added=0;
        for(Cosmetic item:catalog())if(item.kind.equals("title")&&owned.add("title:"+item.id))added++;
        if(added>0)commit(id,new Profile(current.icon,current.title,current.banner,owned));
        return added;
    }
    private void commit(UUID id,Profile profile) throws IOException {
        Map<UUID,Profile> next=new LinkedHashMap<>(profiles);next.put(id,profile);
        persist(next,titleOverrides,deletedTitles);
    }
    private void persist(Map<UUID,Profile> next,Map<String,Cosmetic> overrides,Set<String> deleted) throws IOException {
        JsonObject root=new JsonObject(),entries=new JsonObject();root.addProperty("formatVersion",1);
        next.forEach((uuid,value)->entries.add(uuid.toString(),JSON.toJsonTree(value)));root.add("profiles",entries);
        root.add("titleOverrides",JSON.toJsonTree(overrides));root.add("deletedTitles",JSON.toJsonTree(deleted));
        Files.createDirectories(path.getParent());Path temporary=Files.createTempFile(path.getParent(),"profiles-",".tmp");
        try {
            byte[] bytes=JSON.toJson(root).getBytes(java.nio.charset.StandardCharsets.UTF_8);
            try(FileChannel file=FileChannel.open(temporary,StandardOpenOption.WRITE)){ByteBuffer buffer=ByteBuffer.wrap(bytes);while(buffer.hasRemaining())file.write(buffer);file.force(true);}
            if(Files.exists(path))Files.copy(path,path.resolveSibling(path.getFileName()+".bak"),StandardCopyOption.REPLACE_EXISTING);
            try{Files.move(temporary,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}
            catch(AtomicMoveNotSupportedException ignored){Files.move(temporary,path,StandardCopyOption.REPLACE_EXISTING);}
            profiles.clear();profiles.putAll(next);
            titleOverrides=Collections.unmodifiableMap(new LinkedHashMap<>(overrides));deletedTitles=Set.copyOf(deleted);
        }finally{Files.deleteIfExists(temporary);}
    }
}
