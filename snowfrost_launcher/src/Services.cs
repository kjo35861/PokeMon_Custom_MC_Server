using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace Snowfrost
{
    public sealed class WorkProgress
    {
        public string Message; public double Percent;
        public WorkProgress(string message, double percent) { Message = message; Percent = percent; }
    }
    public static class Json
    {
        public static JavaScriptSerializer Serializer() { return new JavaScriptSerializer { MaxJsonLength = 24 * 1024 * 1024, RecursionLimit = 128 }; }
        public static Dictionary<string, object> Object(object value) { return value as Dictionary<string, object> ?? new Dictionary<string, object>(); }
        public static object Get(object value, string key) { object result; return Object(value).TryGetValue(key, out result) ? result : null; }
        public static string Text(object value, string key) { object item = Get(value, key); return item == null ? "" : Convert.ToString(item, CultureInfo.InvariantCulture); }
        public static long Number(object value, string key) { object item = Get(value, key); return item == null ? 0 : Convert.ToInt64(item, CultureInfo.InvariantCulture); }
        public static object[] Array(object value) { IEnumerable list = value as IEnumerable; return value is string || list == null ? new object[0] : list.Cast<object>().ToArray(); }
        public static Dictionary<string, object> Parse(string text) { return Object(Serializer().DeserializeObject(text)); }
        public static string Encode(object value) { return Serializer().Serialize(value); }
        public static void Save(string path, object value)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temp = path + ".tmp-" + Guid.NewGuid().ToString("N");
            File.WriteAllText(temp, Encode(value), new UTF8Encoding(false));
            try { if (File.Exists(path)) File.Replace(temp, path, null); else File.Move(temp, path); }
            finally { if (File.Exists(temp)) File.Delete(temp); }
        }
    }
    public static class SafeFiles
    {
        public static string Join(string root, string relative)
        {
            if (String.IsNullOrWhiteSpace(relative) || relative.IndexOf('\\') >= 0 || Path.IsPathRooted(relative) || relative.IndexOf(':') >= 0)
                throw new InvalidDataException("허용되지 않는 파일 경로입니다.");
            string[] parts = relative.Split('/');
            foreach (string part in parts)
            {
                if (part.Length == 0 || part == "." || part == ".." || part.TrimEnd(' ', '.') != part || part.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 ||
                    Regex.IsMatch(part, @"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])($|\.)", RegexOptions.IgnoreCase))
                    throw new InvalidDataException("허용되지 않는 파일 경로입니다.");
            }
            string prefix = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string path = Path.GetFullPath(Path.Combine(prefix, relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("게임 폴더 밖에는 파일을 적용할 수 없습니다.");
            string parent = path;
            while (parent != null && parent.StartsWith(prefix.TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase))
            {
                if ((File.Exists(parent) || Directory.Exists(parent)) && (File.GetAttributes(parent) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("업데이트 경로에 연결 폴더 또는 링크가 있습니다.");
                if (String.Equals(parent, prefix.TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase)) break;
                parent = Path.GetDirectoryName(parent);
            }
            return path;
        }
        public static string Digest(string path, string algorithm)
        {
            using (HashAlgorithm hash = algorithm == "sha256" ? (HashAlgorithm)SHA256.Create() : SHA1.Create())
            using (FileStream stream = File.OpenRead(path)) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        public static bool Matches(string path, string hash, long? size, string algorithm)
        {
            return File.Exists(path) && (!size.HasValue || new FileInfo(path).Length == size.Value) &&
                String.Equals(Digest(path, algorithm), hash, StringComparison.OrdinalIgnoreCase);
        }
        public static void Replace(string source, string target)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(target));
            if(!String.Equals(Path.GetPathRoot(Path.GetFullPath(source)),Path.GetPathRoot(Path.GetFullPath(target)),StringComparison.OrdinalIgnoreCase))
            {
                string local=target+".commit-"+Guid.NewGuid().ToString("N");
                try { System.IO.File.Copy(source,local); Replace(local,target); System.IO.File.Delete(source); }
                finally { if(System.IO.File.Exists(local))System.IO.File.Delete(local); }
                return;
            }
            if (File.Exists(target)) File.Replace(source, target, null); else File.Move(source, target);
        }
    }
    public sealed class ApiFailure : Exception
    {
        public readonly int Status;
        public ApiFailure(int status) : base("온라인 서비스 요청에 실패했습니다. HTTP " + status) { Status = status; }
    }
    public static class Net
    {
        static readonly HttpClient client = Create();
        internal static Func<HttpRequestMessage,CancellationToken,Task<HttpResponseMessage>> TestSend;
        static HttpClient Create()
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            ServicePointManager.DefaultConnectionLimit = 16;
            HttpClient value = new HttpClient(new HttpClientHandler { AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate });
            value.Timeout = Timeout.InfiniteTimeSpan; value.DefaultRequestHeaders.UserAgent.ParseAdd("PocketmateLauncher/0.2.0"); return value;
        }
        public static Uri Address(string value)
        {
            Uri uri;
            if (!Uri.TryCreate(value, UriKind.Absolute, out uri) || uri.UserInfo.Length != 0 ||
                (uri.Scheme != "https" && !(uri.Scheme == "http" && uri.IsLoopback)))
                throw new InvalidDataException("업데이트 주소는 HTTPS 주소를 사용해주세요. 로컬 테스트만 HTTP를 허용합니다.");
            return uri;
        }
        public static async Task<string> Text(string url, CancellationToken cancel)
        {
            using (CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel))
            {
                timeout.CancelAfter(TimeSpan.FromSeconds(30));
                using (HttpResponseMessage response = await client.GetAsync(Address(url), HttpCompletionOption.ResponseHeadersRead, timeout.Token))
                {
                    Address(response.RequestMessage.RequestUri.AbsoluteUri);
                    if (!response.IsSuccessStatusCode) throw new ApiFailure((int)response.StatusCode);
                    using (Stream stream = await response.Content.ReadAsStreamAsync())
                    using (MemoryStream buffer = new MemoryStream())
                    {
                        byte[] bytes = new byte[32768]; int count;
                        while ((count = await stream.ReadAsync(bytes, 0, bytes.Length, timeout.Token)) > 0)
                        { if (buffer.Length + count > 24 * 1024 * 1024) throw new InvalidDataException("응답 파일이 너무 큽니다."); buffer.Write(bytes, 0, count); }
                        return Encoding.UTF8.GetString(buffer.ToArray());
                    }
                }
            }
        }
        public static async Task<Dictionary<string, object>> GetJson(string url, CancellationToken cancel) { return Json.Parse(await Text(url, cancel)); }
        public static async Task<Dictionary<string, object>> Send(string url, object body, string bearer, bool form, CancellationToken cancel)
        {
            using (CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel))
            {
                timeout.CancelAfter(TimeSpan.FromSeconds(40));
                using (HttpRequestMessage request = new HttpRequestMessage(body == null ? HttpMethod.Get : HttpMethod.Post, Address(url)))
                {
                    if (body != null) request.Content = form ? (HttpContent)new FormUrlEncodedContent((IEnumerable<KeyValuePair<string, string>>)body) : new StringContent(Json.Encode(body), Encoding.UTF8, "application/json");
                    if (!String.IsNullOrEmpty(bearer)) request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", bearer);
                    using (HttpResponseMessage response = TestSend == null ? await client.SendAsync(request, timeout.Token) : await TestSend(request,timeout.Token))
                    {
                        if (!response.IsSuccessStatusCode) throw new ApiFailure((int)response.StatusCode);
                        return Json.Parse(await response.Content.ReadAsStringAsync());
                    }
                }
            }
        }
        public static async Task File(string url, string path, string hash, long? size, string algorithm, string reuse, IProgress<WorkProgress> progress, CancellationToken cancel)
        {
            cancel.ThrowIfCancellationRequested();
            if (!Regex.IsMatch(hash ?? "", algorithm == "sha256" ? "^[a-fA-F0-9]{64}$" : "^[a-fA-F0-9]{40}$")) throw new InvalidDataException("파일 검증값이 올바르지 않습니다.");
            if (SafeFiles.Matches(path, hash, size, algorithm)) return;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temp = path + ".download-" + Guid.NewGuid().ToString("N");
            try
            {
                if (!String.IsNullOrEmpty(reuse) && SafeFiles.Matches(reuse, hash, size, algorithm)) System.IO.File.Copy(reuse, temp);
                else
                {
                    using (CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel))
                    {
                        timeout.CancelAfter(TimeSpan.FromMinutes(8));
                        using (HttpResponseMessage response = await client.GetAsync(Address(url), HttpCompletionOption.ResponseHeadersRead, timeout.Token))
                        {
                            Address(response.RequestMessage.RequestUri.AbsoluteUri);
                            if (!response.IsSuccessStatusCode) throw new ApiFailure((int)response.StatusCode);
                            using (Stream input = await response.Content.ReadAsStreamAsync())
                            using (FileStream output = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None, 131072, true))
                            {
                                byte[] bytes = new byte[131072]; int count; long received = 0;
                                DateTime last = DateTime.MinValue;
                                while ((count = await input.ReadAsync(bytes, 0, bytes.Length, timeout.Token)) > 0)
                                {
                                    received += count;
                                    if (received > (size ?? 2147483648L)) throw new InvalidDataException("다운로드 파일의 크기가 예상보다 큽니다.");
                                    await output.WriteAsync(bytes, 0, count, timeout.Token);
                                    if (progress != null && (DateTime.UtcNow-last).TotalMilliseconds > 180)
                                    { progress.Report(new WorkProgress(Path.GetFileName(path) + " · " + (received / 1048576.0).ToString("0.0") + " MB", size.GetValueOrDefault() > 0 ? received * 100.0 / size.Value : 0)); last = DateTime.UtcNow; }
                                }
                            }
                        }
                    }
                }
                cancel.ThrowIfCancellationRequested();
                if (!SafeFiles.Matches(temp, hash, size, algorithm)) throw new InvalidDataException("다운로드 파일의 검증값이 일치하지 않습니다. 원래 파일은 유지됩니다.");
                SafeFiles.Replace(temp, path);
            }
            finally { if (System.IO.File.Exists(temp)) System.IO.File.Delete(temp); }
        }
    }
    public sealed class ServerFile
    {
        public string Path { get; set; } public string Url { get; set; } public string Sha256 { get; set; } public long Size { get; set; }
    }
    public sealed class PackState
    {
        public string PackVersion { get; set; } public List<ServerFile> Files { get; set; }
        public PackState() { PackVersion = ""; Files = new List<ServerFile>(); }
    }
    public sealed class UpdatePlan
    {
        public string PackVersion; public string Loader = "fabric"; public string LoaderVersion = UpdateService.DefaultFabricVersion;
        public List<ServerFile> Files = new List<ServerFile>(); public List<ServerFile> Downloads = new List<ServerFile>();
        public List<ServerFile> Removes = new List<ServerFile>(); public bool Needed;
    }
    public sealed class UpdateService
    {
        public const string DefaultFabricVersion = "0.20.1";
        public readonly string GameRoot; readonly string dataRoot;
        public UpdateService(string data) : this(data,Path.Combine(data,"game")) { }
        public UpdateService(string data,string gameRoot) { dataRoot = data; GameRoot = gameRoot; }
        public static void ValidatePath(string path, string root)
        {
            SafeFiles.Join(root, path);
            string top = path.Split('/')[0];
            if (!new[] { "mods", "resourcepacks", "config", "shaderpacks" }.Contains(top, StringComparer.OrdinalIgnoreCase) || path.Split('/').Length < 2)
                throw new InvalidDataException("서버 업데이트는 mods, resourcepacks, config, shaderpacks 폴더에만 적용할 수 있습니다.");
        }
        public PackState ReadState()
        {
            string path = Path.Combine(dataRoot, "pack-state.json");
            if (!System.IO.File.Exists(path)) return new PackState();
            return Json.Serializer().Deserialize<PackState>(System.IO.File.ReadAllText(path, Encoding.UTF8)) ?? new PackState();
        }
        public async Task<UpdatePlan> Check(string url, CancellationToken cancel)
        {
            if (String.IsNullOrWhiteSpace(url)) return null;
            Dictionary<string, object> manifest = await Net.GetJson(url, cancel);
            if (Json.Number(manifest, "formatVersion") != 1 || Json.Text(manifest, "serverId") != "pocketmate" || Json.Text(manifest, "minecraftVersion") != "1.21.1")
                throw new InvalidDataException("포켓메이트 Minecraft 1.21.1용 업데이트 목록이 아닙니다.");
            UpdatePlan plan = new UpdatePlan { PackVersion = Json.Text(manifest, "packVersion") };
            if (plan.PackVersion.Length == 0 || plan.PackVersion.Length > 100) throw new InvalidDataException("팩 버전이 올바르지 않습니다.");
            object loader = Json.Get(manifest, "loader");
            if (loader != null)
            {
                plan.Loader = Json.Text(loader, "type"); plan.LoaderVersion = Json.Text(loader, "version");
                if(plan.Loader=="fabric" && plan.LoaderVersion.Length==0)plan.LoaderVersion=DefaultFabricVersion;
                if (plan.Loader != "vanilla" && ((!new[]{"fabric","neoforge"}.Contains(plan.Loader)) || !Regex.IsMatch(plan.LoaderVersion, @"^[0-9]+\.[0-9]+\.[0-9]+$")))
                    throw new InvalidDataException("현재 업데이트는 Vanilla, Fabric 또는 NeoForge 로더를 지원합니다.");
            }
            object[] entries = Json.Array(Json.Get(manifest, "files"));
            if (!manifest.ContainsKey("files") || !(manifest["files"] is object[])) throw new InvalidDataException("업데이트 파일 목록이 빠져 있습니다.");
            if (entries.Length > 4096) throw new InvalidDataException("업데이트 파일 수가 너무 많습니다.");
            HashSet<string> paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (object entry in entries)
            {
                if (!new[] {"path","url","sha256","size"}.All(k => Json.Object(entry).ContainsKey(k))) throw new InvalidDataException("업데이트 파일의 필수 정보가 빠져 있습니다.");
                ServerFile file = new ServerFile { Path = Json.Text(entry, "path"), Url = Json.Text(entry, "url"), Sha256 = Json.Text(entry, "sha256").ToLowerInvariant(), Size = Json.Number(entry, "size") };
                ValidatePath(file.Path, GameRoot); Net.Address(file.Url);
                if (!paths.Add(file.Path) || !Regex.IsMatch(file.Sha256, "^[a-f0-9]{64}$") || file.Size < 0 || file.Size > 2147483648L)
                    throw new InvalidDataException("업데이트 파일 정보 또는 중복 경로를 확인해주세요.");
                if (file.Path.StartsWith("mods/", StringComparison.OrdinalIgnoreCase) && plan.Loader == "vanilla")
                    throw new InvalidDataException("모드 파일을 사용하려면 업데이트 목록에 Fabric 또는 NeoForge 로더를 지정해야 합니다.");
                plan.Files.Add(file);
                if (!SafeFiles.Matches(SafeFiles.Join(GameRoot, file.Path), file.Sha256, file.Size, "sha256")) plan.Downloads.Add(file);
            }
            PackState previous = ReadState();
            foreach (ServerFile old in previous.Files ?? new List<ServerFile>())
            { ValidatePath(old.Path, GameRoot); if (!paths.Contains(old.Path) && System.IO.File.Exists(SafeFiles.Join(GameRoot, old.Path))) plan.Removes.Add(old); }
            Tuple<string,string> priorLoader = Loader(null);
            plan.Needed = previous.PackVersion != plan.PackVersion || plan.Downloads.Count > 0 || plan.Removes.Count > 0 || priorLoader.Item1 != plan.Loader || priorLoader.Item2 != plan.LoaderVersion;
            return plan;
        }
        public async Task Apply(UpdatePlan plan, IProgress<WorkProgress> progress, CancellationToken cancel, Dictionary<string,object> metadata = null)
        {
            if (plan == null) return;
            string job = Path.Combine(dataRoot, "updates", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N"));
            string staging = Path.Combine(job, "staging"), backups = Path.Combine(job, "backup");
            Directory.CreateDirectory(staging);
            int index = 0;
            foreach (ServerFile file in plan.Downloads)
            {
                progress.Report(new WorkProgress("서버 파일 다운로드 " + (++index) + "/" + plan.Downloads.Count + " · " + file.Path, index*70.0/Math.Max(1,plan.Downloads.Count)));
                await Net.File(file.Url, SafeFiles.Join(staging, file.Path), file.Sha256, file.Size, "sha256", null, null, cancel);
            }
            cancel.ThrowIfCancellationRequested();
            List<Tuple<string, string, bool>> committed = new List<Tuple<string, string, bool>>();
            try
            {
                foreach (ServerFile file in plan.Downloads.Concat(plan.Removes))
                {
                    string target = SafeFiles.Join(GameRoot, file.Path), backup = SafeFiles.Join(backups, file.Path);
                    bool exists = System.IO.File.Exists(target);
                    if (exists) { Directory.CreateDirectory(Path.GetDirectoryName(backup)); System.IO.File.Copy(target, backup); }
                    if (plan.Downloads.Contains(file)) SafeFiles.Replace(SafeFiles.Join(staging, file.Path), target);
                    else if (exists) System.IO.File.Delete(target);
                    committed.Add(Tuple.Create(target, backup, exists));
                }
                if (metadata!=null) foreach(var item in metadata)
                {
                    string backup=Path.Combine(job,"metadata-"+committed.Count+".backup");bool exists=System.IO.File.Exists(item.Key);
                    if(exists)System.IO.File.Copy(item.Key,backup);
                    Json.Save(item.Key,item.Value);committed.Add(Tuple.Create(item.Key,backup,exists));
                }
                string[] names = {"loader-state.json","pack-state.json"};
                object[] states = {new {type=plan.Loader,version=plan.LoaderVersion}, new PackState { PackVersion=plan.PackVersion,Files=plan.Files }};
                for (int i=0;i<names.Length;i++)
                {
                    string target=Path.Combine(dataRoot,names[i]),backup=Path.Combine(job,names[i]+".backup");bool exists=System.IO.File.Exists(target);
                    if(exists) System.IO.File.Copy(target,backup);
                    Json.Save(target,states[i]);committed.Add(Tuple.Create(target,backup,exists));
                }
                progress.Report(new WorkProgress("서버 업데이트 완료", 100));
            }
            catch
            {
                foreach (Tuple<string, string, bool> item in Enumerable.Reverse(committed))
                { if (item.Item3) System.IO.File.Copy(item.Item2, item.Item1, true); else if (System.IO.File.Exists(item.Item1)) System.IO.File.Delete(item.Item1); }
                throw;
            }
        }
        public Tuple<string, string> Loader(UpdatePlan plan)
        {
            if (plan != null) return Tuple.Create(plan.Loader, plan.LoaderVersion);
            string path = Path.Combine(dataRoot, "loader-state.json");
            if (!System.IO.File.Exists(path)) return Tuple.Create("vanilla", "");
            object state = Json.Parse(System.IO.File.ReadAllText(path)); return Tuple.Create(Json.Text(state, "type"), Json.Text(state, "version"));
        }
    }
}
