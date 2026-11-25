using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace Snowfrost
{
    public sealed class QuietProgress : IProgress<WorkProgress> { public void Report(WorkProgress progress) { } }
    public static class BackendTests
    {
        static void Check(bool value,string name,List<string> checks) { if(!value) throw new Exception("Verification failed: "+name); checks.Add(name); }
        public static async Task Run(string report,string root,string fixture)
        {
            Directory.CreateDirectory(root);List<string> checks=new List<string>();
            string[] invalid={"../mods/escape.jar","mods/../escape.jar","mods\\escape.jar","C:/escape.jar","config/CON.txt","config/unsafe:stream","resourcepacks/a.","versions/evil.jar"};
            foreach(string path in invalid) { bool rejected=false;try{UpdateService.ValidatePath(path,root);}catch(InvalidDataException){rejected=true;} Check(rejected,"Reject path "+path,checks); }
            bool unsafeUrl=false;try{Net.Address("http://example.com/manifest.json");}catch(InvalidDataException){unsafeUrl=true;}Check(unsafeUrl,"Require HTTPS outside loopback",checks);
            Check(Net.Address("http://127.0.0.1:1234/manifest.json").IsLoopback,"Allow local update fixture",checks);
            Check(MicrosoftLogin.Challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")=="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM","RFC7636 PKCE vector",checks);
            Check(MicrosoftLogin.ReadCode("/?code=hello&state=wrong","right")==null,"Reject mismatched OAuth state",checks);
            Check(MicrosoftLogin.ReadCode("/?code=hello%2Bworld&state=right","right")=="hello+world","Accept matching OAuth state",checks);
            Check(GameInstaller.SelectLoader(false,Tuple.Create("fabric","0.16.14")).Item1=="vanilla","No server always selects vanilla even after Fabric",checks);
            string client="12345678-1234-4123-8123-123456789abc";
            string url=MicrosoftLogin.LoginUrl(client,"state","verifier");
            Check(url.StartsWith("https://login.live.com/")&&url.Contains("code_challenge_method=S256")&&!url.Contains("client_secret"),"Public-client browser auth",checks);
            AccountVault vault=new AccountVault(root);
            AccountSession expired=new AccountSession{ClientId=client,Name="Test",Uuid=new string('a',32),AccessToken="MOCK_OLD_TOKEN",RefreshToken="MOCK_REFRESH",ExpiresUtc=DateTime.UtcNow.AddMinutes(-5)};
            vault.Save(expired);
            Check(!File.ReadAllText(Path.Combine(root,"account.bin")).Contains("MOCK_REFRESH")&&vault.Read().Name=="Test","DPAPI token encryption round-trip",checks);
            int calls=0;
            Net.TestSend=delegate(HttpRequestMessage request,CancellationToken cancellation){
                calls++;object data;
                switch(request.RequestUri.Host+request.RequestUri.AbsolutePath)
                {
                    case "login.live.com/oauth20_token.srf":data=new{access_token="MOCK_MSA",refresh_token="MOCK_REFRESH_NEXT"};break;
                    case "user.auth.xboxlive.com/user/authenticate":data=new{Token="MOCK_XBOX"};break;
                    case "xsts.auth.xboxlive.com/xsts/authorize":data=new{Token="MOCK_XSTS",DisplayClaims=new{xui=new[]{new{uhs="hash",xid="123"}}}};break;
                    case "api.minecraftservices.com/authentication/login_with_xbox":data=new{access_token="MOCK_MINECRAFT",expires_in=3600};break;
                    case "api.minecraftservices.com/minecraft/profile":data=new{name="VerifiedTest",id=new string('b',32)};break;
                    default:throw new Exception("Unexpected auth endpoint");
                }
                return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){Content=new StringContent(Json.Encode(data))});
            };
            try
            {
                AccountSession refreshed=await MicrosoftLogin.Ensure(client,vault,new QuietProgress(),CancellationToken.None);
                Check(calls==5&&refreshed.Name=="VerifiedTest"&&refreshed.AccessToken=="MOCK_MINECRAFT","Refresh + Xbox + Minecraft + profile auth chain",checks);
                int before=calls;await MicrosoftLogin.Ensure(client,vault,new QuietProgress(),CancellationToken.None);
                Check(calls==before,"Valid account avoids repeat login",checks);
            }
            finally{Net.TestSend=null;}
            if(!String.IsNullOrWhiteSpace(fixture))
            {
                UpdateService service=new UpdateService(Path.Combine(root,"updates-test"));IProgress<WorkProgress> progress=new QuietProgress();
                Check(await service.Check("",CancellationToken.None)==null,"No server configured uses vanilla mode",checks);
                UpdatePlan defaults=await service.Check(fixture+"manifest-default-fabric.json",CancellationToken.None);
                Check(defaults.Loader=="fabric"&&defaults.LoaderVersion==UpdateService.DefaultFabricVersion,"Server manifest defaults to pinned Fabric",checks);
                UpdatePlan first=await service.Check(fixture+"manifest-v1.json",CancellationToken.None);
                Check(first.Needed&&first.Downloads.Count==2,"Initial server pack requires update",checks);
                await service.Apply(first,progress,CancellationToken.None);
                Check(!(await service.Check(fixture+"manifest-v1.json",CancellationToken.None)).Needed,"Installed pack is current",checks);
                service.VerifyApprovedContent(first);
                string extra = SafeFiles.Join(service.GameRoot,"resourcepacks/unlisted.zip");
                File.WriteAllText(extra,"fixture");
                bool extraBlocked = false;
                try { service.VerifyApprovedContent(first); }
                catch (InvalidDataException) { extraBlocked = true; }
                File.Delete(extra);
                Check(extraBlocked,"Unlisted resource pack blocks managed launch",checks);
                string localRoot = Path.Combine(root,"local-client-pack");
                string localSource = Path.Combine(localRoot,"client-files","fixture.jar");
                Directory.CreateDirectory(Path.GetDirectoryName(localSource));
                File.WriteAllText(localSource,"local mod fixture");
                string manifestPath = Path.Combine(localRoot,"client-pack.json");
                var localService = new UpdateService(Path.Combine(localRoot,"state"),Path.Combine(localRoot,"instance"));
                Json.Save(manifestPath,new {formatVersion=1,serverId="pocketmate",minecraftVersion="1.21.1",packVersion="local-fixture",loader=new {type="neoforge",version="21.1.248"},files=new[]{
                    new {path="mods/fixture.jar",url="local:fixture.jar",sha256=SafeFiles.Digest(localSource,"sha256"),size=new FileInfo(localSource).Length}
                }});
                var localPlan = localService.CheckLocal(manifestPath);
                await localService.Apply(localPlan,progress,CancellationToken.None);
                Check(localPlan.Needed && File.ReadAllText(Path.Combine(localService.GameRoot,"mods","fixture.jar"))=="local mod fixture" &&
                    !localService.CheckLocal(manifestPath).Needed,"Editable local client pack installs and verifies its listed file",checks);
                Json.Save(manifestPath,new {formatVersion=1,serverId="pocketmate",minecraftVersion="1.21.1",packVersion="local-fixture",loader=new {type="neoforge",version="21.1.248"},files=new object[0]});
                var localRemoval = localService.CheckLocal(manifestPath);
                await localService.Apply(localRemoval,progress,CancellationToken.None);
                Check(!File.Exists(Path.Combine(localService.GameRoot,"mods","fixture.jar")),"Removing a managed client pack entry uninstalls it",checks);
                string file=SafeFiles.Join(service.GameRoot,"config/managed.json");string original=File.ReadAllText(file);
                File.WriteAllText(file,"damaged");
                UpdatePlan repair=await service.Check(fixture+"manifest-v1.json",CancellationToken.None);
                Check(repair.Downloads.Count==1,"Changed same-version file needs repair",checks);
                await service.Apply(repair,progress,CancellationToken.None);Check(File.ReadAllText(file)==original,"Repair restores verified bytes",checks);
                string pack=SafeFiles.Join(service.GameRoot,"resourcepacks/test.zip");string oldHash=SafeFiles.Digest(pack,"sha256");
                UpdatePlan bad=await service.Check(fixture+"manifest-bad.json",CancellationToken.None);bool refused=false;
                try{await service.Apply(bad,progress,CancellationToken.None);}catch(InvalidDataException){refused=true;}
                Check(refused&&File.ReadAllText(file)==original&&SafeFiles.Digest(pack,"sha256")==oldHash&&service.ReadState().PackVersion=="1","Bad SHA leaves prior pack intact",checks);
                UpdatePlan locked=await service.Check(fixture+"manifest-locked.json",CancellationToken.None);bool rolled=false;
                using(FileStream hold=new FileStream(pack,FileMode.Open,FileAccess.Read,FileShare.Read))
                {try{await service.Apply(locked,progress,CancellationToken.None);}catch(IOException){rolled=true;}}
                Check(rolled&&File.ReadAllText(file)==original&&SafeFiles.Digest(pack,"sha256")==oldHash&&service.ReadState().PackVersion=="1","Apply failure rolls back earlier files",checks);
                string personal=SafeFiles.Join(service.GameRoot,"config/personal.txt");File.WriteAllText(personal,"keep");
                UpdatePlan next=await service.Check(fixture+"manifest-v2.json",CancellationToken.None);await service.Apply(next,progress,CancellationToken.None);
                Check(!File.Exists(file)&&File.ReadAllText(personal)=="keep"&&service.ReadState().PackVersion=="2","Remove only previously managed obsolete files",checks);
                foreach(string suffix in new[]{"manifest-version.json","manifest-traversal.json","manifest-missing-files.json","manifest-duplicates.json","manifest-mods-without-loader.json"})
                {bool rejected=false;try{await service.Check(fixture+suffix,CancellationToken.None);}catch(InvalidDataException){rejected=true;}Check(rejected,"Reject "+suffix,checks);}
                UpdatePlan fabric=await service.Check(fixture+"manifest-fabric.json",CancellationToken.None);
                Check(fabric.Loader=="fabric"&&fabric.LoaderVersion=="0.16.14","Fabric loader is selected from server manifest",checks);
            }
            await PrismChecks(root,fixture,checks);
            Json.Save(report,new{passed=true,checks=checks.Count,cases=checks,realMicrosoftLoginPerformed=false,gameLaunched=false});
        }
        static async Task PrismChecks(string root,string fixture,List<string> checks)
        {
            string data=Path.Combine(root,"Prism data"),instances=Path.Combine(root,"Custom instances");
            Directory.CreateDirectory(data);Directory.CreateDirectory(instances);
            File.WriteAllText(Path.Combine(data,"prismlauncher.cfg"),"[General]\nInstanceDir="+instances.Replace('\\','/')+"\n");
            string vanilla=Path.Combine(instances,"1.21.1 test");Directory.CreateDirectory(vanilla);
            string exe=Path.Combine(data,"prismlauncher.exe");File.WriteAllText(exe,"TEST FIXTURE ONLY - NEVER EXECUTED");
            File.WriteAllText(Path.Combine(vanilla,"instance.cfg"),"[General]\nInstanceType=OneSix\nname=Test\n");
            object clean=new{formatVersion=1,components=new[]{new{uid="net.minecraft",version="1.21.1",important=true}}};
            Json.Save(Path.Combine(vanilla,"mmc-pack.json"),clean);
            Directory.CreateDirectory(Path.Combine(vanilla,".minecraft"));
            Settings config=new Settings{PrismPath=exe,PrismDataPath=data,PrismInstanceId="1.21.1 test"};
            PrismTarget plain=PrismBridge.Resolve(config);
            Check(plain.GameRoot.EndsWith(".minecraft")&&plain.InstancesRoot==instances,"Prism respects custom InstanceDir and legacy .minecraft",checks);
            config.PrismInstanceId="../escape";bool bad=false;try{PrismBridge.Resolve(config);}catch(InvalidDataException){bad=true;}Check(bad,"Prism rejects escaped instance ID",checks);config.PrismInstanceId="1.21.1 test";
            Json.Save(Path.Combine(vanilla,"mmc-pack.json"),new{formatVersion=1,components=new[]{new{uid="net.minecraft",version="1.21.4"}}});
            Check(!PrismBridge.Vanilla1211(vanilla),"Prism rejects a different Minecraft version",checks);Json.Save(Path.Combine(vanilla,"mmc-pack.json"),clean);
            string original=File.ReadAllText(Path.Combine(vanilla,"mmc-pack.json"));
            PrismTarget server=PrismBridge.ServerTarget(plain,Path.Combine(root,"owner"));PrismBridge.EnsureServer(server,plain);
            Check(server.GameRoot!=plain.GameRoot && File.ReadAllText(Path.Combine(vanilla,"mmc-pack.json"))==original,"Server instance is isolated from original vanilla",checks);
            string optionsPath = Path.Combine(server.GameRoot, "options.txt");
            string initialOptions = File.ReadAllText(optionsPath);
            Check(initialOptions.Contains("chatLineSpacing:0.3573943661971831") && initialOptions.Contains("chatScale:0.7059859154929577") && initialOptions.Contains("lang:ko_kr"), "New server instances seed chat and display options", checks);
            File.WriteAllText(optionsPath, "chatLineSpacing:0.6");
            string before=File.ReadAllText(Path.Combine(server.Root,"instance.cfg"));PrismBridge.EnsureServer(server,plain);
            Check(before==File.ReadAllText(Path.Combine(server.Root,"instance.cfg")),"Existing managed instance settings are preserved",checks);
            Check(File.ReadAllText(optionsPath) == "chatLineSpacing:0.6", "Existing player options are preserved", checks);
            File.Delete(optionsPath);
            PrismBridge.EnsureServer(server, plain);
            Check(!File.Exists(optionsPath), "Existing instances are not reseeded when options are missing", checks);

            UpdatePlan fabric=new UpdatePlan{Loader="fabric",LoaderVersion="0.16.14"};
            Json.Save(Path.Combine(server.Root,"mmc-pack.json"),PrismBridge.LoaderPack(server,fabric));
            Check(PrismBridge.LoaderMatches(server,fabric)&&!PrismBridge.Vanilla1211(server.Root),"Fabric component is installed only into server instance",checks);
            UpdatePlan neo=new UpdatePlan{Loader="neoforge",LoaderVersion="21.1.123"};
            Json.Save(Path.Combine(server.Root,"mmc-pack.json"),PrismBridge.LoaderPack(server,neo));
            Check(PrismBridge.LoaderMatches(server,neo),"NeoForge component replaces prior Fabric component",checks);
            UpdatePlan vanillaPlan=new UpdatePlan{Loader="vanilla",LoaderVersion=""};Json.Save(Path.Combine(server.Root,"mmc-pack.json"),PrismBridge.LoaderPack(server,vanillaPlan));
            Check(PrismBridge.LoaderMatches(server,vanillaPlan)&&PrismBridge.Vanilla1211(vanilla),"Switching server loader back to vanilla leaves base untouched",checks);
            var command=PrismBridge.Command(plain);
            Check(command.FileName==exe && command.Arguments=="--dir "+GameInstaller.Quote(data)+" --launch "+GameInstaller.Quote("1.21.1 test")&&!command.Arguments.Contains("token"),"Prism CLI quotes paths and sends no credentials",checks);
            Check(PrismBridge.Command(server,"localhost:25565").Arguments.EndsWith(" --server "+GameInstaller.Quote("localhost:25565")) &&
                  !PrismBridge.Command(plain,"localhost:25565").Arguments.Contains(" --server "), "Auto join is limited to the managed server instance", checks);
            Check(PrismBridge.MatchesProcess("java -Djava.library.path="+plain.Root.Replace('\\','/')+"/natives",plain)&&!PrismBridge.MatchesProcess("java -Djava.library.path="+plain.Root+"-other/natives",plain),"Process detection respects instance path boundary",checks);
            if(!String.IsNullOrWhiteSpace(fixture))
            {
                UpdateService service=new UpdateService(Path.Combine(root,"prism-update-state"),server.GameRoot);
                UpdatePlan first=await service.Check(fixture+"manifest-v1.json",CancellationToken.None);
                await service.Apply(first,new QuietProgress(),CancellationToken.None,new Dictionary<string,object>{{Path.Combine(server.Root,"mmc-pack.json"),PrismBridge.LoaderPack(server,first)}});
                Check(File.Exists(Path.Combine(server.GameRoot,"config","managed.json"))&&!Directory.Exists(Path.Combine(plain.GameRoot,"config")),"Updates land in selected Prism server game directory",checks);
                string configFile=Path.Combine(server.GameRoot,"config","managed.json"),old=File.ReadAllText(configFile);
                UpdatePlan next=await service.Check(fixture+"manifest-locked.json",CancellationToken.None);bool rolled=false;
                using(FileStream hold=new FileStream(Path.Combine(server.Root,"mmc-pack.json"),FileMode.Open,FileAccess.Read,FileShare.Read))
                {try{await service.Apply(next,new QuietProgress(),CancellationToken.None,new Dictionary<string,object>{{Path.Combine(server.Root,"mmc-pack.json"),clean}});}catch(IOException){rolled=true;}}
                Check(rolled&&File.ReadAllText(configFile)==old&&service.ReadState().PackVersion=="1","Locked Prism loader metadata rolls back changed content",checks);
                UpdatePlan neoManifest=await service.Check(fixture+"manifest-neoforge.json",CancellationToken.None);
                Check(neoManifest.Loader=="neoforge"&&neoManifest.LoaderVersion=="21.1.123","Server manifest accepts pinned NeoForge version",checks);
            }
        }
        public static async Task Install(string report,string dataRoot)
        {
            InstalledGame game=await new GameInstaller(dataRoot).Install("",Tuple.Create("fabric","0.16.14"),new QuietProgress(),CancellationToken.None,true);
            AccountSession mock=new AccountSession{ClientId="TEST_ONLY",Name="InstallCheck",Uuid=new string('a',32),AccessToken="TEST_ONLY_NOT_REAL",ExpiresUtc=DateTime.UtcNow.AddHours(1)};
            var command=GameInstaller.Command(game,mock,4096);
            if(!command.Arguments.Contains("\"--version\" \"1.21.1\"")||!game.Classpath.Split(';').All(File.Exists)||game.MainClass!="net.minecraft.client.main.Main"||!game.GameRoot.EndsWith("vanilla-1.21.1"))throw new Exception("Invalid vanilla Minecraft installation or launch command");
            Json.Save(report,new{passed=true,minecraftVersion=GameInstaller.Version,javaMajor=GameInstaller.JavaMajor(game.JavaPath),classpathFiles=game.Classpath.Split(';').Length,
                nativeDlls=Directory.GetFiles(game.Natives,"*.dll").Length,gameDirectory=game.GameRoot,commandVersionPinned=true,isolatedVanilla=true,mainClass=game.MainClass,realAccountUsed=false,gameLaunched=false});
        }
        public static async Task PrismLaunch(string report,Settings settings)
        {
            PrismTarget target=PrismBridge.Resolve(settings);
            Process prior=PrismBridge.FindGame(target);
            if(prior!=null){prior.Dispose();throw new InvalidOperationException("Close the existing Minecraft instance before the launch test.");}
            using(Process game=await PrismBridge.Start(target,new QuietProgress(),CancellationToken.None))
            {
                string title="";bool initialized=false;
                for(int i=0;i<60;i++)
                {
                    await Task.Delay(1000);game.Refresh();if(game.HasExited)throw new Exception("Game exited before initialization");
                    title=game.MainWindowTitle;
                    string log=Path.Combine(target.GameRoot,"logs","latest.log");
                    if(File.Exists(log)) using(FileStream stream=new FileStream(log,FileMode.Open,FileAccess.Read,FileShare.ReadWrite))using(StreamReader reader=new StreamReader(stream))
                    { string content=reader.ReadToEnd();initialized=content.Contains("textures/atlas/gui.png-atlas")||content.Contains("textures/atlas/particles.png-atlas"); }
                    if(title.Contains("1.21.1")&&initialized)break;
                }
                if(!title.Contains("1.21.1")||!initialized)throw new Exception("Minecraft title or resource initialization was not observed");
                using(Process duplicate=PrismBridge.FindGame(target))
                {if(duplicate==null||duplicate.Id!=game.Id)throw new Exception("Running instance cannot be detected");}
                bool closing=game.CloseMainWindow();
                bool closed=closing && await Task.Run(()=>game.WaitForExit(20000));
                Json.Save(report,new{passed=closed,minecraftVersion=GameInstaller.Version,prismInstance=target.Id,gameDirectory=target.GameRoot,windowTitle=title,resourcesInitialized=initialized,duplicateDetection=true,gameLaunched=true,closedAfterTest=closed,accountFilesRead=false,customClientIdRequired=false});
                if(!closed)throw new Exception("Test game did not close normally");
            }
        }
    }
}
