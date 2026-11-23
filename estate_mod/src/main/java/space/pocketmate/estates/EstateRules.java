package space.pocketmate.estates;

/** Whole-won prices. Each upgrade cost is the price of entering that level. */
public final class EstateRules {
    private EstateRules() {}
    public static final int MAX_LEVEL=10;
    public static final long MAX_MONEY=9_000_000_000_000L;
    private static final int[] LIMITS={1,4,6,9,12,16,20,24,28,32,36};
    private static final int[] MEMBER_LIMITS={5,5,5,5,5,5,5,5,5,5,5};
    public static int memberLimit(int level){if(level<0||level>MAX_LEVEL)throw new IllegalArgumentException();return MEMBER_LIMITS[level];}
    private static final long[] UPGRADE_COSTS={0,0,50_000,100_000,200_000,350_000,550_000,800_000,1_100_000,1_500_000,2_000_000};
    public static int limit(int level){if(level<0||level>MAX_LEVEL)throw new IllegalArgumentException();return LIMITS[level];}
    public static long cost(int targetLevel){if(targetLevel<0||targetLevel>MAX_LEVEL)throw new IllegalArgumentException();return UPGRADE_COSTS[targetLevel];}
    public static int migrationLevel(int chunks){for(int level=0;level<MAX_LEVEL;level++)if(chunks<=LIMITS[level])return level;return MAX_LEVEL;}
    public static long nextChunkPrice(int purchasedChunks){if(purchasedChunks<1||purchasedChunks>1_000_000)throw new IllegalArgumentException();return purchasedChunks<4?0:20_000L+2_500L*(purchasedChunks-4);}
    public static long purchasePrice(int purchasedChunks,int count){if(count<1||count>128)throw new IllegalArgumentException();long sum=0;for(int i=0;i<count;i++)sum=Math.addExact(sum,nextChunkPrice(purchasedChunks+i));return sum;}
}
