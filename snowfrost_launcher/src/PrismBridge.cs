using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Management;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Snowfrost
{
    public sealed class PrismTarget
    {
        public string Executable, DataRoot, InstancesRoot, Id, Root, GameRoot;
        public bool Managed;
    }
    public static class PrismBridge
    {
        static readonly string[] LoaderIds = { "net.fabricmc.fabric-loader", "net.neoforged", "net.minecraftforge", "org.quiltmc.quilt-loader" };
        public static string Ini(string path, string key)
        {
            if (!File.Exists(path)) return "";
            bool general = false;
            foreach (string raw in File.ReadAllLines(path))
            {
                string line = raw.Trim();
                if (line.StartsWith("[")) { general = line == "[General]"; continue; }
                if (general && line.StartsWith(key+"=",StringComparison.OrdinalIgnoreCase)) return line.Substring(key.Length+1).Trim();
            }
            return "";
        }
        public static string InstanceDirectory(string data)
        {
            string configured = Ini(Path.Combine(data,"prismlauncher.cfg"),"InstanceDir");
            if (configured.Length == 0) configured = "instances";
            return Path.GetFullPath(Path.IsPathRooted(configured) ? configured : Path.Combine(data,configured));
        }
        public static string GameDirectory(string root)
        {
            string normal = Path.Combine(root,"minecraft"), dot = Path.Combine(root,".minecraft");
            return Directory.Exists(dot) && !Directory.Exists(normal) ? dot : normal;
        }
        public static string Key(string value)
        {
            using (SHA256 hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(Path.GetFullPath(value).ToLowerInvariant()))).Replace("-","").Substring(0,16).ToLowerInvariant();
        }
        public static bool Vanilla1211(string root)
        {
            try
            {
                object pack = Json.Parse(File.ReadAllText(Path.Combine(root,"mmc-pack.json")));
                object[] components = Json.Array(Json.Get(pack,"components"));
                return components.Any(c => Json.Text(c,"uid")=="net.minecraft" && Json.Text(c,"version")==GameInstaller.Version) &&
                    !components.Any(c => LoaderIds.Contains(Json.Text(c,"uid")));
            }
            catch { return false; }
        }
        public static void Discover(Settings settings)
        {
            if (String.IsNullOrWhiteSpace(settings.PrismPath))
            {
                string[] candidates = {
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","PrismLauncher","prismlauncher.exe"),
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"PrismLauncher","prismlauncher.exe"),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"PrismLauncher","prismlauncher.exe") };
                settings.PrismPath = candidates.FirstOrDefault(File.Exists) ?? "";
            }
            if (String.IsNullOrWhiteSpace(settings.PrismDataPath))
            {
                string portable = String.IsNullOrWhiteSpace(settings.PrismPath) ? "" : Path.GetDirectoryName(settings.PrismPath);
                settings.PrismDataPath = portable.Length>0 && File.Exists(Path.Combine(portable,"portable.txt")) ? portable : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),"PrismLauncher");
            }
            if (String.IsNullOrWhiteSpace(settings.PrismInstanceId))
            {
                string instances = InstanceDirectory(settings.PrismDataPath);
                if (Directory.Exists(instances))
                {
                    string[] available = Directory.GetDirectories(instances).Where(Vanilla1211).OrderBy(p => Path.GetFileName(p)=="1.21.1" ? 0 : 1).ThenBy(p=>p).ToArray();
                    if (available.Length>0) settings.PrismInstanceId = Path.GetFileName(available[0]);
                }
            }
        }
        public static PrismTarget Resolve(Settings settings)
        {
            Discover(settings);
            if (!File.Exists(settings.PrismPath) || !String.Equals(Path.GetFileName(settings.PrismPath),"prismlauncher.exe",StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Prism Launcher를 설치하고 설정에서 prismlauncher.exe를 선택해주세요.");
            if (String.IsNullOrWhiteSpace(settings.PrismInstanceId)) throw new InvalidOperationException("Prism에서 순정 Minecraft 1.21.1 인스턴스를 만든 뒤 설정에서 인스턴스 ID를 지정해주세요.");
            string id = settings.PrismInstanceId;
            if (id.IndexOfAny(new[]{'/', '\\', ':'})>=0 || id=="." || id=="..") throw new InvalidDataException("인스턴스 ID에는 폴더 이름만 입력해주세요.");
            string data=Path.GetFullPath(settings.PrismDataPath), instances=InstanceDirectory(data), root=SafeFiles.Join(instances,id);
            if (!File.Exists(Path.Combine(root,"instance.cfg")) || !Vanilla1211(root))
                throw new InvalidOperationException("선택한 Prism 인스턴스는 순정 Minecraft 1.21.1이어야 합니다. 모드가 없는 1.21.1 인스턴스를 선택해주세요.");
            return new PrismTarget { Executable=Path.GetFullPath(settings.PrismPath),DataRoot=data,InstancesRoot=instances,Id=id,Root=root,GameRoot=GameDirectory(root) };
        }
        public static PrismTarget ResolveNeoForgeTest(PrismTarget vanilla, string id)
        {
            if (id.IndexOfAny(new[]{'/', (char)92, ':'}) >= 0 || id == "." || id == "..")
                throw new InvalidDataException("테스트 인스턴스 ID에는 폴더 이름만 입력해주세요.");
            string root = SafeFiles.Join(vanilla.InstancesRoot, id);
            if (!File.Exists(Path.Combine(root, "instance.cfg")))
                throw new InvalidOperationException("NeoForge 테스트 인스턴스가 없습니다.");
            object[] components = Json.Array(Json.Get(Json.Parse(File.ReadAllText(Path.Combine(root, "mmc-pack.json"))), "components"));
            if (!components.Any(c => Json.Text(c,"uid") == "net.minecraft" && Json.Text(c,"version") == GameInstaller.Version) ||
                !components.Any(c => Json.Text(c,"uid") == "net.neoforged" && Json.Text(c,"version") == "21.1.248") ||
                components.Count(c => LoaderIds.Contains(Json.Text(c,"uid"))) != 1)
                throw new InvalidOperationException("테스트 인스턴스는 Minecraft 1.21.1 / NeoForge 21.1.248이어야 합니다.");
            return new PrismTarget { Executable=vanilla.Executable, DataRoot=vanilla.DataRoot,
                InstancesRoot=vanilla.InstancesRoot, Id=id, Root=root, GameRoot=GameDirectory(root), Managed=true };
        }
        public static PrismTarget ServerTarget(PrismTarget vanilla,string owner)
        {
            string id="Pocketmate-Server-"+Key(vanilla.Root+Path.DirectorySeparatorChar+Key(owner));
            string root=SafeFiles.Join(vanilla.InstancesRoot,id);
            return new PrismTarget { Executable=vanilla.Executable,DataRoot=vanilla.DataRoot,InstancesRoot=vanilla.InstancesRoot,Id=id,Root=root,GameRoot=GameDirectory(root),Managed=true };
        }
        public static void EnsureServer(PrismTarget target,PrismTarget vanilla)
        {
            string marker=Path.Combine(target.Root,"pocketmate-instance.json");
            if (Directory.Exists(target.Root) && !File.Exists(marker)) throw new IOException("같은 이름의 Prism 폴더가 이미 있습니다. 기존 폴더를 덮어쓰지 않았습니다.");
            bool creating = !File.Exists(marker);
            Directory.CreateDirectory(target.Root);
            // Only our own server instance is created. Never copy accounts, worlds, commands or launcher secrets.
            Json.Save(marker,new{formatVersion=1,vanillaRoot=vanilla.Root});
            if (!File.Exists(Path.Combine(target.Root,"mmc-pack.json"))) Json.Save(Path.Combine(target.Root,"mmc-pack.json"),Json.Parse(File.ReadAllText(Path.Combine(vanilla.Root,"mmc-pack.json"))));
            if (!File.Exists(Path.Combine(target.Root,"instance.cfg")))
                File.WriteAllText(Path.Combine(target.Root,"instance.cfg"),"[General]\nConfigVersion=1.3\nInstanceType=OneSix\nname=Pocketmate Server 1.21.1\nuuid="+Guid.NewGuid().ToString("N")+"\n",new UTF8Encoding(false));
            if (creating) WriteInitialOptions(target.GameRoot);
        }
        private static void WriteInitialOptions(string gameRoot)
        {
            Directory.CreateDirectory(gameRoot);
            string path = Path.Combine(gameRoot, "options.txt");
            if (File.Exists(path)) return;
            // Seed only the selected chat and display settings from the test instance.
            string[] defaults = {
                "version:3955", "lang:ko_kr", "guiScale:0",
                "chatVisibility:0", "chatColors:true", "chatLinks:true", "chatLinksPrompt:true",
                "chatOpacity:1.0", "chatDelay:0.0", "chatWidth:1.0",
                "chatHeightFocused:1.0", "chatHeightUnfocused:0.4375",
                "chatLineSpacing:0.3573943661971831", "chatScale:0.7059859154929577"
            };
            using (var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write))
            using (var writer = new StreamWriter(file, new UTF8Encoding(false)))
                foreach (string line in defaults) writer.WriteLine(line);
        }
        public static object LoaderPack(PrismTarget target,UpdatePlan plan)
        {
            if (!target.Managed) throw new InvalidOperationException("순정 인스턴스의 로더는 변경하지 않습니다.");
            Dictionary<string,object> pack=Json.Parse(File.ReadAllText(Path.Combine(target.Root,"mmc-pack.json")));
            var components=Json.Array(Json.Get(pack,"components")).Where(c=>!LoaderIds.Contains(Json.Text(c,"uid")) && Json.Text(c,"uid")!="net.fabricmc.intermediary" && Json.Text(c,"uid")!="org.quiltmc.hashed").ToList();
            if (!components.Any(c=>Json.Text(c,"uid")=="net.minecraft" && Json.Text(c,"version")==GameInstaller.Version)) throw new InvalidDataException("서버 인스턴스의 Minecraft 버전이 1.21.1이 아닙니다.");
            if (plan.Loader!="vanilla") components.Add(new Dictionary<string,object>{{"uid",plan.Loader=="fabric"?"net.fabricmc.fabric-loader":"net.neoforged"},{"version",plan.LoaderVersion},{"important",true}});
            pack["components"]=components.ToArray();return pack;
        }
        public static bool LoaderMatches(PrismTarget target,UpdatePlan plan)
        {
            if (!File.Exists(Path.Combine(target.Root,"mmc-pack.json"))) return false;
            object[] parts=Json.Array(Json.Get(Json.Parse(File.ReadAllText(Path.Combine(target.Root,"mmc-pack.json"))),"components"));
            object[] loaders=parts.Where(c=>LoaderIds.Contains(Json.Text(c,"uid"))).ToArray();
            return plan.Loader=="vanilla" ? loaders.Length==0 : loaders.Length==1 && Json.Text(loaders[0],"uid")== (plan.Loader=="fabric"?"net.fabricmc.fabric-loader":"net.neoforged") && Json.Text(loaders[0],"version")==plan.LoaderVersion;
        }
        public static ProcessStartInfo Command(PrismTarget target,string serverAddress=null)
        {
            return new ProcessStartInfo(target.Executable,"--dir "+GameInstaller.Quote(target.DataRoot)+" --launch "+GameInstaller.Quote(target.Id)+(target.Managed&&!String.IsNullOrEmpty(serverAddress)?" --server "+GameInstaller.Quote(serverAddress):""))
                {UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,WorkingDirectory=Path.GetDirectoryName(target.Executable)};
        }
        public static bool MatchesProcess(string command,PrismTarget target)
        {
            // Prism's Java bootstrap refers to <instance>/natives, not necessarily its minecraft subfolder.
            return (command??"").Replace('\\','/').IndexOf(target.Root.Replace('\\','/').TrimEnd('/')+"/",StringComparison.OrdinalIgnoreCase)>=0;
        }
        public static Process FindGame(params PrismTarget[] targets)
        {
            // Inspect process identity only. Command lines are never logged or returned to the UI.
            using (ManagementObjectSearcher search = new ManagementObjectSearcher("SELECT ProcessId,CommandLine FROM Win32_Process WHERE Name='javaw.exe' OR Name='java.exe'"))
            {
                search.Options.Timeout=TimeSpan.FromSeconds(3);
                using (ManagementObjectCollection rows=search.Get())
                foreach (ManagementObject row in rows)
                using (row)
                {
                    if (!targets.Any(t=>t!=null && MatchesProcess(Convert.ToString(row["CommandLine"]),t))) continue;
                    try { Process process=Process.GetProcessById(Convert.ToInt32(row["ProcessId"])); if(!process.HasExited)return process; process.Dispose(); }catch(ArgumentException){}
                }
            }
            return null;
        }
        static long LogLength(string path)
        {
            try { return new FileInfo(path).Length; }
            catch (IOException) { return 0; }
            catch (UnauthorizedAccessException) { return 0; }
        }
        static bool InstanceRejected(string path, long start, string id)
        {
            try
            {
                using (var stream = new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite | FileShare.Delete))
                {
                    stream.Seek(start <= stream.Length ? Math.Max(start, stream.Length - 65536) : Math.Max(0,stream.Length - 65536),SeekOrigin.Begin);
                    using (var reader = new StreamReader(stream,Encoding.UTF8))
                    {
                        string line;
                        while ((line = reader.ReadLine()) != null)
                            if (line.Contains("Launch command requires an valid instance ID") && line.Contains("\""+id+"\"") && line.Contains("resolves to nothing"))
                                return true;
                    }
                }
            }
            catch (IOException) {}
            catch (UnauthorizedAccessException) {}
            return false;
        }
        public static async Task<Process> Start(PrismTarget target,IProgress<WorkProgress> progress,CancellationToken cancel,string serverAddress=null)
        {
            string log = Path.Combine(target.DataRoot,"logs","PrismLauncher-0.log");
            long previousLogLength = LogLength(log);
            using(Process request=Process.Start(Command(target,serverAddress)))
            {
                DateTime until=DateTime.UtcNow.AddMinutes(3);
                while (DateTime.UtcNow<until)
                {
                    cancel.ThrowIfCancellationRequested();
                    Process game=await Task.Run(()=>FindGame(target));if(game!=null)return game;
                    if(InstanceRejected(log,previousLogLength,target.Id))
                        throw new InvalidOperationException("Prism이 테스트 인스턴스를 목록에서 찾지 못했습니다. Prism을 완전히 종료한 뒤 게임 시작을 다시 눌러주세요.");
                    if(request.HasExited && request.ExitCode!=0)throw new InvalidOperationException("Prism이 실행 요청을 처리하지 못했습니다. Prism에서 이 인스턴스가 실행되는지 확인해주세요.");
                    progress.Report(new WorkProgress("Prism에서 Minecraft 시작 중 · 로그인이 필요하면 Prism 화면에서 진행해주세요.",0));
                    await Task.Delay(900,cancel);
                }
            }
            throw new TimeoutException("Prism에 실행을 요청했지만 게임 시작을 확인하지 못했습니다. Prism의 로그인 또는 오류 안내를 확인해주세요.");
        }
    }
}
