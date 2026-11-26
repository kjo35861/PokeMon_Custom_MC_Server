"""Stage NeoForge sources from the same gameplay source tree used by Fabric."""
from pathlib import Path
import json
import os
import re
import shutil

here = Path(__file__).resolve().parent
base = here.parent
stage = Path(os.environ["LOCALAPPDATA"]) / "PocketmateNeoForgeBuild"
stage.mkdir(exist_ok=True)
for name in ("settings.gradle", "build.gradle", "gradle.properties"):
    shutil.copyfile(here / name, stage / name)
resources = stage / "src/main/resources"
shutil.copytree(base / "src/main/resources", resources, dirs_exist_ok=True)
(resources / "fabric.mod.json").unlink(missing_ok=True)
for path in (base / "src/main/java").rglob("*.java"):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^import net\.fabricmc\..*;\n", "", text, flags=re.M)
    text = re.sub(r" implements (?:Client)?ModInitializer", "", text)
    text = re.sub(r"@Override(?=\s+public void onInitialize)", "", text)
    for old, new in {
        "FabricLoader.getInstance().getConfigDir()": "net.neoforged.fml.loading.FMLPaths.CONFIGDIR.get()",
        "FabricLoader.getInstance().isModLoaded": "net.neoforged.fml.ModList.get().isLoaded",
        "ServerLifecycleEvents.SERVER_STARTING.register": "NeoEvents.starting",
        "ServerLifecycleEvents.SERVER_STOPPED.register": "NeoEvents.stopped",
        "ServerTickEvents.START_SERVER_TICK.register": "NeoEvents.beforeTick",
        "ServerTickEvents.END_SERVER_TICK.register": "NeoEvents.afterTick",
        "CommandRegistrationCallback.EVENT.register": "NeoEvents.commands",
        "ServerPlayConnectionEvents.JOIN.register((handler,sender,server)->": "NeoEvents.join((player,server)->",
        "ServerPlayConnectionEvents.DISCONNECT.register((handler,server)->": "NeoEvents.leave((player,server)->",
        "handler.player": "player",
        "PlayerBlockBreakEvents.AFTER.register": "NeoEvents.blockBroken",
        "ClientTickEvents.END_CLIENT_TICK.register": "NeoClientEvents.afterTick",
        "ClientPlayConnectionEvents.DISCONNECT.register((handler,client)->": "NeoClientEvents.disconnect(client->",
        "ClientPlayNetworking.registerGlobalReceiver(NicknamePayload.ID,": "NeoClientEvents.nickname(",
        "ServerPlayNetworking.canSend(p,NicknamePayload.ID)": "NeoEvents.canSendNickname(p)",
        "ServerPlayNetworking.send(p,new NicknamePayload(required,message))": "NeoEvents.sendNickname(p,new NicknamePayload(required,message))",
        "        PayloadTypeRegistry.playS2C().register(NicknamePayload.ID,NicknamePayload.CODEC);\n": "",
    }.items():
        text = text.replace(old, new)
    if path.name == "WalletSidebar.java":
        text = text.replace("networkHandler.sendPacket(", "networkHandler.send(")
    if path.name == "ShopAssetsClient.java":
        start = text.index("  ResourceManagerHelper.get")
        end = text.index("\n }",start)
        text = text[:start] + "  NeoClientEvents.reload(manager -> MinecraftClient.getInstance().execute(() -> {cache.clear();jobs.clear();}));" + text[end:]
    target = stage / "src/main/java" / path.relative_to(base / "src/main/java")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(text,encoding="utf-8")

shutil.copytree(here / "src", stage / "src", dirs_exist_ok=True)
alpha = base.parent / "webgui_menu/transparency_fix"
target = stage / "src/main/java/space/pocketmate/webgui/mixin/GuiTransparencyMixin.java"
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text((alpha / "src/space/pocketmate/webgui/mixin/GuiTransparencyMixin.java").read_text().replace('{"method_25394", "render"}','"render"'),encoding="utf-8")
shutil.copyfile(alpha / "pocketmate-webgui-alpha.mixins.json",resources / "pocketmate-webgui-alpha.mixins.json")
mixins_file = resources / "pocketmate-estates.mixins.json"
mixins = json.loads(mixins_file.read_text())
mixins["mixins"].append("NeoMissionBreakMixin")
mixins["mixins"].append("PixelmonTeraShardMessageMixin")
mixins_file.write_text(json.dumps(mixins, indent=2) + "\n")
shutil.copytree(base / "src/test", stage / "src/test", dirs_exist_ok=True)
print(stage)
