package space.pocketmate.estates;

/** Xaero stores emitted light in alpha; it is not transparency. */
public final class MapPixelCodec {
    private MapPixelCodec() {}
    public static int daylightArgb(int red,int green,int blue,int emittedLight) {
        int rgb=((red&255)<<16)|((green&255)<<8)|(blue&255);
        return rgb==0?0:0xff000000|rgb;
    }
}
