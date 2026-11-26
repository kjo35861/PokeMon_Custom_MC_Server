package space.pocketmate.mega.client;

/** Display labels only; registry IDs, commands and saved items remain unchanged. */
public final class TooltipBranding {
    private TooltipBranding() {}

    public static String displayLine(String namespace, String path, String line) {
        if ("eeveemega".equals(namespace) && (namespace + ":" + path).equals(line)) {
            return "PocketMate_Mega / " + path;
        }
        return line;
    }
}
