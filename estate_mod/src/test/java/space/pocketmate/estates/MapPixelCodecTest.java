package space.pocketmate.estates;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class MapPixelCodecTest {
    @Test void unlitTerrainIsOpaqueInsteadOfDisappearing() {
        assertEquals(0xff417b28,MapPixelCodec.daylightArgb(65,123,40,0));
        assertEquals(0xff417b28,MapPixelCodec.daylightArgb(65,123,40,255));
        assertEquals(0xff214d9b,MapPixelCodec.daylightArgb(33,77,155,0));
    }
    @Test void absentTerrainRemainsUnknown() {assertEquals(0,MapPixelCodec.daylightArgb(0,0,0,0));}
}
