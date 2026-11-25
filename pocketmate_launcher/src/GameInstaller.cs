using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace Snowfrost
{
    public sealed class InstalledGame
    {
        public string JavaPath, GameRoot, AssetsRoot, LibrariesRoot, MainClass, Classpath, Natives, AssetIndex, LoggingArgument;
        public Dictionary<string, object> Version;
        public object ExtraJvm, ExtraGame;
    }
    public sealed class GameInstaller
    {
        public const string Version = "1.21.1";
        public readonly string GameRoot;
        readonly string global;
        public GameInstaller(string data) { GameRoot = Path.Combine(data, "game"); global = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), ".minecraft"); }
        public static bool Allowed(object item)
        {
            object rules = Json.Get(item, "rules");
            if (rules == null) return true;
            bool allowed = false;
            foreach (object rule in Json.Array(rules))
            {
                object os = Json.Get(rule, "os"); bool matches = true;
                string name = Json.Text(os, "name"), arch = Json.Text(os, "arch"), version = Json.Text(os, "version");
                if (name.Length > 0 && name != "windows") matches = false;
                if (arch.Length > 0 && !Regex.IsMatch(Environment.Is64BitProcess ? "amd64" : "x86", arch)) matches = false;
                if (version.Length > 0 && !Regex.IsMatch(Environment.OSVersion.Version.ToString(), version)) matches = false;
                foreach (KeyValuePair<string, object> feature in Json.Object(Json.Get(rule,"features")))
                    if (Convert.ToBoolean(feature.Value) != (feature.Key == "has_custom_resolution")) matches = false;
                if (matches) allowed = Json.Text(rule, "action") == "allow";
            }
            return allowed;
        }
        async Task<string> Artifact(object artifact, string root, string reuseRoot, CancellationToken cancel)
        {
            string relative = Json.Text(artifact, "path");
            string target = SafeFiles.Join(root, relative);
            string reuse = reuseRoot == null ? null : SafeFiles.Join(reuseRoot, relative);
            object size = Json.Get(artifact, "size");
            await Net.File(Json.Text(artifact,"url"), target, Json.Text(artifact,"sha1"), size == null ? (long?)null : Convert.ToInt64(size), "sha1", reuse, null, cancel);
            return target;
        }
        public static int JavaMajor(string path)
        {
            if (!File.Exists(path)) return 0;
            string probe = path.EndsWith("javaw.exe", StringComparison.OrdinalIgnoreCase) ? Path.Combine(Path.GetDirectoryName(path), "java.exe") : path;
            if (!File.Exists(probe)) return 0;
            try
            {
                ProcessStartInfo start = new ProcessStartInfo(probe, "-version") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden, RedirectStandardError = true, RedirectStandardOutput = true };
                using (Process process = Process.Start(start))
                {
                    Task<string> output = process.StandardError.ReadToEndAsync(); Task<string> other = process.StandardOutput.ReadToEndAsync();
                    if (!process.WaitForExit(6000)) { process.Kill(); return 0; }
                    Match match = Regex.Match(output.Result + " " + other.Result, @"version ""([0-9]+)");
                    return match.Success ? Int32.Parse(match.Groups[1].Value) : 0;
                }
            }
            catch { return 0; }
        }
        string FindJava(string custom)
        {
            if (!String.IsNullOrWhiteSpace(custom))
            {
                if (JavaMajor(custom) != 21) throw new InvalidOperationException("Minecraft 1.21.1 실행을 위해 Java 21 실행 파일을 선택해주세요.");
                return custom;
            }
            List<string> roots = new List<string> { Path.Combine(GameRoot, "runtime") };
            foreach (string program in new[] { Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86) })
                foreach (string name in new[] { "Java", "Eclipse Adoptium", "Microsoft" }) roots.Add(Path.Combine(program, name));
            roots.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Packages", "Microsoft.4297127D64EC6_8wekyb3d8bbwe", "LocalCache", "Local", "runtime", "java-runtime-delta"));
            roots.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".lunarclient", "jre"));
            foreach (string root in roots)
            {
                if (!Directory.Exists(root)) continue;
                try
                {
                    foreach (string file in Directory.GetFiles(root, "javaw.exe", SearchOption.AllDirectories))
                        if ((file.IndexOf("21",StringComparison.Ordinal) >= 0 || file.IndexOf("java-runtime-delta",StringComparison.Ordinal) >= 0) && JavaMajor(file) == 21) return file;
                }
                catch (UnauthorizedAccessException) { }
            }
            return null;
        }
        async Task<string> EnsureJava(string custom, IProgress<WorkProgress> progress, CancellationToken cancel)
        {
            string installed = FindJava(custom); if (installed != null) return installed;
            progress.Report(new WorkProgress("Java 21 설치 파일 확인 중", 0));
            object manifest = await Net.GetJson("https://launchermeta.mojang.com/v1/products/java-runtime/2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json", cancel);
            object[] versions = Json.Array(Json.Get(Json.Get(manifest,"windows-x64"),"java-runtime-delta"));
            object selected = versions.FirstOrDefault(v => Json.Text(Json.Get(v,"version"),"name").StartsWith("21",StringComparison.Ordinal));
            if (selected == null) throw new InvalidOperationException("Java 21 다운로드 정보를 찾지 못했습니다. 설정에서 설치된 Java 21 경로를 지정해주세요.");
            object descriptor = Json.Get(selected, "manifest");
            string descriptorPath = SafeFiles.Join(GameRoot,"runtime-manifest.json");
            await Net.File(Json.Text(descriptor,"url"), descriptorPath, Json.Text(descriptor,"sha1"), Json.Number(descriptor,"size"), "sha1", null, null, cancel);
            object files = Json.Get(Json.Parse(File.ReadAllText(descriptorPath)), "files");
            string root = Path.Combine(GameRoot,"runtime","java-runtime-delta"); int done = 0, total = Json.Object(files).Count;
            foreach (KeyValuePair<string, object> file in Json.Object(files))
            {
                cancel.ThrowIfCancellationRequested(); string target = SafeFiles.Join(root, file.Key); string type = Json.Text(file.Value,"type");
                if (type == "directory") Directory.CreateDirectory(target);
                else if (type == "file")
                {
                    object raw = Json.Get(Json.Get(file.Value,"downloads"),"raw");
                    await Net.File(Json.Text(raw,"url"), target, Json.Text(raw,"sha1"), Json.Number(raw,"size"), "sha1", null, null, cancel);
                }
                else throw new InvalidDataException("지원하지 않는 Java 런타임 파일 형식입니다.");
                progress.Report(new WorkProgress("Java 21 준비 중 · " + (++done) + "/" + total, done*100.0/total));
            }
            installed = Path.Combine(root,"bin","javaw.exe");
            if (JavaMajor(installed) != 21) throw new InvalidDataException("설치한 Java 21을 확인하지 못했습니다.");
            return installed;
        }
        public static Tuple<string,string> SelectLoader(bool serverConfigured,Tuple<string,string> serverLoader) { return serverConfigured ? serverLoader : Tuple.Create("vanilla",""); }
        public async Task<InstalledGame> Install(string customJava, Tuple<string,string> loader, IProgress<WorkProgress> progress, CancellationToken cancel, bool isolatedVanilla = false)
        {
            if (isolatedVanilla) loader = Tuple.Create("vanilla","");
            Directory.CreateDirectory(GameRoot);
            progress.Report(new WorkProgress("Minecraft 1.21.1 배포 정보 확인 중", 0));
            object manifest = await Net.GetJson("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", cancel);
            object release = Json.Array(Json.Get(manifest,"versions")).FirstOrDefault(v => Json.Text(v,"id") == Version);
            if (release == null) throw new InvalidDataException("공식 Minecraft 1.21.1 배포 정보를 찾지 못했습니다.");
            string versionRoot = Path.Combine(GameRoot,"versions",Version); Directory.CreateDirectory(versionRoot);
            string versionPath = Path.Combine(versionRoot,Version+".json");
            await Net.File(Json.Text(release,"url"), versionPath, Json.Text(release,"sha1"), null, "sha1", Path.Combine(global,"versions",Version,Version+".json"), null, cancel);
            Dictionary<string,object> version = Json.Parse(File.ReadAllText(versionPath));
            if (Json.Text(version,"id") != Version) throw new InvalidDataException("Minecraft 버전이 일치하지 않습니다.");
            string java = await EnsureJava(customJava,progress,cancel);
            object client = Json.Get(Json.Get(version,"downloads"),"client");
            string jar = Path.Combine(versionRoot,Version+".jar");
            progress.Report(new WorkProgress("Minecraft 1.21.1 클라이언트 확인 중", 0));
            await Net.File(Json.Text(client,"url"), jar, Json.Text(client,"sha1"), Json.Number(client,"size"), "sha1", Path.Combine(global,"versions",Version,Version+".jar"),progress,cancel);
            List<object> libraries = Json.Array(Json.Get(version,"libraries")).ToList();
            object fabric = null;
            if (loader.Item1 == "fabric")
            {
                if (!Regex.IsMatch(loader.Item2,@"^[0-9]+\.[0-9]+\.[0-9]+$")) throw new InvalidDataException("Fabric 버전이 올바르지 않습니다.");
                fabric = await Net.GetJson("https://meta.fabricmc.net/v2/versions/loader/1.21.1/"+loader.Item2+"/profile/json",cancel);
                if (Json.Text(fabric,"inheritsFrom") != Version) throw new InvalidDataException("Minecraft 1.21.1용 Fabric 프로필이 아닙니다.");
                libraries.AddRange(Json.Array(Json.Get(fabric,"libraries")));
                Json.Save(Path.Combine(GameRoot,"fabric-profile.json"),fabric);
            }
            else if (loader.Item1 != "vanilla") throw new InvalidDataException("지원하지 않는 모드 로더입니다.");
            List<string> classpath = new List<string>(), natives = new List<string>();
            string libraryRoot = Path.Combine(GameRoot,"libraries"); int done = 0;
            foreach (object library in libraries)
            {
                cancel.ThrowIfCancellationRequested(); if (!Allowed(library)) continue;
                string name = Json.Text(library,"name");
                if (name.Contains("natives-windows-arm64") || name.Contains("natives-windows-x86")) continue;
                progress.Report(new WorkProgress("게임 라이브러리 확인 중 · " + (++done) + "/" + libraries.Count, done*100.0/libraries.Count));
                object downloads = Json.Get(library,"downloads"), artifact = Json.Get(downloads,"artifact");
                if (artifact != null)
                {
                    string file = await Artifact(artifact,libraryRoot,Path.Combine(global,"libraries"),cancel);
                    classpath.Add(file); if (name.Contains("natives-windows")) natives.Add(file);
                }
                else
                {
                    string[] parts = name.Split(':');
                    if (parts.Length != 3 || !Regex.IsMatch(name,@"^[A-Za-z0-9_.:\-]+$")) throw new InvalidDataException("라이브러리 이름이 올바르지 않습니다.");
                    string relative = parts[0].Replace('.','/')+"/"+parts[1]+"/"+parts[2]+"/"+parts[1]+"-"+parts[2]+".jar";
                    string baseUrl = Json.Text(library,"url"); if (baseUrl.Length == 0) baseUrl = "https://libraries.minecraft.net/";
                    string url = baseUrl.TrimEnd('/')+"/"+relative;
                    string hash = (await Net.Text(url+".sha1",cancel)).Trim().Split(' ')[0];
                    string file = SafeFiles.Join(libraryRoot,relative);
                    await Net.File(url,file,hash,null,"sha1",SafeFiles.Join(Path.Combine(global,"libraries"),relative),null,cancel); classpath.Add(file);
                }
                string classifier = Json.Text(Json.Get(library,"natives"),"windows");
                if (classifier.Length != 0)
                {
                    classifier = classifier.Replace("${arch}","64"); object native = Json.Get(Json.Get(downloads,"classifiers"),classifier);
                    if (native != null) natives.Add(await Artifact(native,libraryRoot,Path.Combine(global,"libraries"),cancel));
                }
            }
            classpath.Add(jar);
            string nativeRoot = Path.Combine(GameRoot,"natives",loader.Item1+"-"+Version); Directory.CreateDirectory(nativeRoot);
            foreach (string native in natives.Distinct())
                using (ZipArchive archive = ZipFile.OpenRead(native))
                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        if (!entry.FullName.EndsWith(".dll",StringComparison.OrdinalIgnoreCase)) continue;
                        string target = SafeFiles.Join(nativeRoot,Path.GetFileName(entry.FullName));
                        using (Stream input = entry.Open()) using (FileStream output = File.Create(target)) input.CopyTo(output);
                    }
            object assetIndex = Json.Get(version,"assetIndex"); string assetId = Json.Text(assetIndex,"id");
            string assets = Path.Combine(GameRoot,"assets"), indexFile = SafeFiles.Join(assets,"indexes/"+assetId+".json");
            await Net.File(Json.Text(assetIndex,"url"),indexFile,Json.Text(assetIndex,"sha1"),Json.Number(assetIndex,"size"),"sha1",SafeFiles.Join(Path.Combine(global,"assets"),"indexes/"+assetId+".json"),null,cancel);
            var objects = Json.Object(Json.Get(Json.Parse(File.ReadAllText(indexFile)),"objects")).Values.ToArray();
            int completed = 0; SemaphoreSlim slots = new SemaphoreSlim(8);
            await Task.WhenAll(objects.Select(async entry => {
                await slots.WaitAsync(cancel);
                try
                {
                    string hash = Json.Text(entry,"hash");
                    if (!Regex.IsMatch(hash,"^[a-f0-9]{40}$")) throw new InvalidDataException("게임 에셋 검증값이 올바르지 않습니다.");
                    string relative = "objects/"+hash.Substring(0,2)+"/"+hash;
                    await Net.File("https://resources.download.minecraft.net/"+hash.Substring(0,2)+"/"+hash,SafeFiles.Join(assets,relative),hash,Json.Number(entry,"size"),"sha1",SafeFiles.Join(Path.Combine(global,"assets"),relative),null,cancel);
                    int count = Interlocked.Increment(ref completed);
                    if (count % 40 == 0 || count == objects.Length) progress.Report(new WorkProgress("게임 리소스 확인 중 · "+count+"/"+objects.Length,count*100.0/objects.Length));
                }
                finally { slots.Release(); }
            }));
            slots.Dispose();
            string loggingArgument = null; object logging = Json.Get(Json.Get(version,"logging"),"client");
            if (logging != null)
            {
                object file = Json.Get(logging,"file"); string relative = "log_configs/"+Json.Text(file,"id");
                string path = SafeFiles.Join(assets,relative);
                await Net.File(Json.Text(file,"url"),path,Json.Text(file,"sha1"),Json.Number(file,"size"),"sha1",SafeFiles.Join(Path.Combine(global,"assets"),relative),null,cancel);
                loggingArgument = Json.Text(logging,"argument").Replace("${path}",path);
            }
            progress.Report(new WorkProgress("Minecraft 1.21.1 실행 준비 완료",100));
            string launchDirectory = isolatedVanilla ? Path.Combine(Path.GetDirectoryName(GameRoot),"vanilla-1.21.1") : GameRoot;
            Directory.CreateDirectory(launchDirectory);
            return new InstalledGame { JavaPath=java,GameRoot=launchDirectory,AssetsRoot=assets,LibrariesRoot=libraryRoot,MainClass=Json.Text(fabric??version,"mainClass"),Classpath=String.Join(";",classpath.Distinct()),Natives=nativeRoot,AssetIndex=assetId,Version=version,
                ExtraGame=Json.Get(Json.Get(fabric,"arguments"),"game"),ExtraJvm=Json.Get(Json.Get(fabric,"arguments"),"jvm"),LoggingArgument=loggingArgument };
        }
        public static string Quote(string value)
        {
            StringBuilder result = new StringBuilder("\""); int slashes = 0;
            foreach (char character in value)
            { if (character == '\\') slashes++; else { if (character == '"') result.Append('\\',slashes*2+1); else result.Append('\\',slashes); result.Append(character); slashes=0; } }
            result.Append('\\',slashes*2); result.Append('"'); return result.ToString();
        }
        static IEnumerable<string> Arguments(object list, Dictionary<string,string> replacements)
        {
            foreach (object item in Json.Array(list))
            {
                object value = item;
                if (!(item is string)) { if (!Allowed(item)) continue; value = Json.Get(item,"value"); }
                foreach (object argument in value is string ? new object[] { value } : Json.Array(value))
                {
                    string text = Convert.ToString(argument);
                    foreach (var pair in replacements) text = text.Replace("${"+pair.Key+"}",pair.Value??"");
                    if (Regex.IsMatch(text,@"\$\{[^}]+\}")) throw new InvalidDataException("알 수 없는 Minecraft 실행 인수가 있습니다.");
                    yield return text;
                }
            }
        }
        public static ProcessStartInfo Command(InstalledGame game, AccountSession account, int memory)
        {
            if (account == null || String.IsNullOrWhiteSpace(account.AccessToken) || account.ExpiresUtc <= DateTime.UtcNow) throw new InvalidOperationException("Minecraft 로그인이 필요합니다.");
            var values = new Dictionary<string,string> { {"auth_player_name",account.Name},{"auth_uuid",account.Uuid},{"auth_access_token",account.AccessToken},{"auth_xuid",account.Xuid??""},
                {"clientid",account.ClientId},{"version_name",Version},{"version_type","release"},{"user_type","msa"},{"user_properties","{}"},
                {"game_directory",game.GameRoot},{"assets_root",game.AssetsRoot??Path.Combine(game.GameRoot,"assets")},{"assets_index_name",game.AssetIndex},
                {"natives_directory",game.Natives},{"classpath",game.Classpath},{"classpath_separator",";"},{"library_directory",game.LibrariesRoot??Path.Combine(game.GameRoot,"libraries")},
                {"launcher_name","Pocketmate"},{"launcher_version","0.2.0"},{"resolution_width","1280"},{"resolution_height","720"} };
            var args = new List<string> { "-Xms512M", "-Xmx"+Math.Max(1024,Math.Min(16384,memory))+"M" };
            object metadataArgs = Json.Get(game.Version,"arguments");
            args.AddRange(Arguments(Json.Get(metadataArgs,"jvm"),values)); args.AddRange(Arguments(game.ExtraJvm,values));
            if (!String.IsNullOrEmpty(game.LoggingArgument)) args.Add(game.LoggingArgument);
            args.Add(game.MainClass); args.AddRange(Arguments(Json.Get(metadataArgs,"game"),values)); args.AddRange(Arguments(game.ExtraGame,values));
            return new ProcessStartInfo(game.JavaPath,String.Join(" ",args.Select(Quote))) { WorkingDirectory=game.GameRoot,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true };
        }
        public static Process Start(InstalledGame game, AccountSession account, int memory, string dataRoot)
        {
            Process process = new Process { StartInfo = Command(game,account,memory), EnableRaisingEvents=true };
            string path = Path.Combine(dataRoot,"game-output.log"); object gate = new object();
            DataReceivedEventHandler output = delegate(object sender,DataReceivedEventArgs e) {
                if (e.Data == null) return; string line = e.Data.Replace(account.AccessToken,"[TOKEN]");
                if (!String.IsNullOrEmpty(account.RefreshToken)) line = line.Replace(account.RefreshToken,"[TOKEN]");
                try { lock(gate) File.AppendAllText(path,line+Environment.NewLine,Encoding.UTF8); } catch { }
            };
            process.OutputDataReceived += output; process.ErrorDataReceived += output;
            process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine(); return process;
        }
    }
}
