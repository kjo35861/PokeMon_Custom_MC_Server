using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web;

namespace Snowfrost
{
    public sealed class AccountSession
    {
        public string ClientId { get; set; }
        public string Name { get; set; }
        public string Uuid { get; set; }
        public string Xuid { get; set; }
        public string AccessToken { get; set; }
        public string RefreshToken { get; set; }
        public DateTime ExpiresUtc { get; set; }
    }
    public sealed class AccountVault
    {
        readonly string path;
        static readonly byte[] purpose = Encoding.UTF8.GetBytes("Pocketmate/Account/v1");
        public AccountVault(string root) { path = Path.Combine(root, "account.bin"); }
        public AccountSession Read()
        {
            if (!File.Exists(path)) return null;
            try
            {
                byte[] bytes = ProtectedData.Unprotect(File.ReadAllBytes(path), purpose, DataProtectionScope.CurrentUser);
                try { return Json.Serializer().Deserialize<AccountSession>(Encoding.UTF8.GetString(bytes)); }
                finally { Array.Clear(bytes, 0, bytes.Length); }
            }
            catch (CryptographicException) { return null; }
        }
        public void Save(AccountSession session)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            byte[] clear = Encoding.UTF8.GetBytes(Json.Encode(session));
            byte[] encrypted;
            try { encrypted = ProtectedData.Protect(clear, purpose, DataProtectionScope.CurrentUser); }
            finally { Array.Clear(clear, 0, clear.Length); }
            string temporary = path + ".tmp";
            File.WriteAllBytes(temporary, encrypted); SafeFiles.Replace(temporary, path);
        }
        public void Forget() { if (File.Exists(path)) File.Delete(path); }
    }
    public static class MicrosoftLogin
    {
        public const string Redirect = "http://localhost:52741/";
        public static string RandomUrlSafe(int bytes)
        {
            byte[] value = new byte[bytes]; using (RandomNumberGenerator random = RandomNumberGenerator.Create()) random.GetBytes(value);
            return Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        }
        public static string Challenge(string verifier)
        {
            using (SHA256 sha = SHA256.Create()) return Convert.ToBase64String(sha.ComputeHash(Encoding.ASCII.GetBytes(verifier))).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        }
        public static string LoginUrl(string client, string state, string verifier)
        {
            Guid id; if (!Guid.TryParse(client, out id)) throw new InvalidOperationException("Microsoft 로그인용 Client ID를 설정해주세요. 동봉한 로그인 연결 안내를 참고하세요.");
            return "https://login.live.com/oauth20_authorize.srf?client_id=" + Uri.EscapeDataString(client) +
                "&response_type=code&redirect_uri=" + Uri.EscapeDataString(Redirect) +
                "&scope=" + Uri.EscapeDataString("XboxLive.signin offline_access") + "&state=" + Uri.EscapeDataString(state) +
                "&code_challenge=" + Challenge(verifier) + "&code_challenge_method=S256&prompt=select_account";
        }
        public static string ReadCode(string target, string expectedState)
        {
            Uri uri = new Uri(new Uri(Redirect), target);
            if (uri.AbsolutePath != "/") return null;
            var query = HttpUtility.ParseQueryString(uri.Query);
            if (query["state"] != expectedState) return null;
            if (!String.IsNullOrEmpty(query["error"])) throw new OperationCanceledException("Microsoft 로그인이 취소되었습니다.");
            return query["code"];
        }
        static async Task<string> ReceiveCode(TcpListener listener, string state, CancellationToken cancel)
        {
            using (CancellationTokenRegistration registration = cancel.Register(delegate { listener.Stop(); }))
            {
                while (true)
                {
                    cancel.ThrowIfCancellationRequested();
                    using (TcpClient client = await listener.AcceptTcpClientAsync())
                    {
                        client.ReceiveTimeout = 4000; client.SendTimeout = 4000;
                        using (NetworkStream stream = client.GetStream())
                        {
                            string line = await Task.Run(delegate {
                                StringBuilder text = new StringBuilder(); int value;
                                while ((value = stream.ReadByte()) != -1 && text.Length < 16384) { if (value == '\n') break; text.Append((char)value); }
                                return text.ToString().TrimEnd('\r');
                            }, cancel);
                            string[] pieces = line.Split(' ');
                            string code = pieces.Length == 3 && pieces[0] == "GET" ? ReadCode(pieces[1], state) : null;
                            string body = code == null ? "Invalid or expired login request. Return to Pocketmate Launcher." :
                                "<!doctype html><meta charset=utf-8><title>Pocketmate</title><body style='background:#16251b;color:#d5efce;font-family:system-ui;text-align:center;padding:12vh 24px'><h1>포켓메이트</h1><p>Microsoft 로그인이 연결되었습니다. 런처로 돌아가주세요.</p></body>";
                            byte[] payload = Encoding.UTF8.GetBytes(body);
                            byte[] header = Encoding.ASCII.GetBytes("HTTP/1.1 " + (code == null ? "400 Bad Request" : "200 OK") + "\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nContent-Security-Policy: default-src 'none'; style-src 'unsafe-inline'\r\nConnection: close\r\nContent-Length: " + payload.Length + "\r\n\r\n");
                            await stream.WriteAsync(header, 0, header.Length, cancel); await stream.WriteAsync(payload, 0, payload.Length, cancel);
                            if (code != null) return code;
                        }
                    }
                }
            }
        }
        static async Task<Dictionary<string, object>> Interactive(string clientId, IProgress<WorkProgress> progress, CancellationToken cancel)
        {
            string state = RandomUrlSafe(32), verifier = RandomUrlSafe(64);
            string url = LoginUrl(clientId, state, verifier);
            TcpListener listener = new TcpListener(IPAddress.Loopback, 52741);
            using (CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel))
            {
                timeout.CancelAfter(TimeSpan.FromMinutes(5));
                try
                {
                    listener.Start(4);
                    progress.Report(new WorkProgress("브라우저에서 Microsoft 로그인을 완료해주세요.", 0));
                    Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
                    string code = await ReceiveCode(listener, state, timeout.Token);
                    return await Net.Send("https://login.live.com/oauth20_token.srf", new Dictionary<string, string> {
                        {"client_id",clientId}, {"redirect_uri",Redirect}, {"grant_type","authorization_code"},
                        {"code",code}, {"code_verifier",verifier}, {"scope","XboxLive.signin offline_access"}}, null, true, cancel);
                }
                catch (SocketException) { if (timeout.IsCancellationRequested) throw new OperationCanceledException("Microsoft 로그인이 취소되었거나 대기 시간이 지났습니다."); throw new InvalidOperationException("로그인 연결 포트(52741)를 사용할 수 없습니다. 다른 포켓메이트 런처를 닫고 다시 시도해주세요."); }
                catch (ObjectDisposedException) { if (timeout.IsCancellationRequested) throw new OperationCanceledException("Microsoft 로그인이 취소되었습니다."); throw; }
                catch (IOException) { if (timeout.IsCancellationRequested) throw new OperationCanceledException("Microsoft 로그인이 취소되었습니다."); throw; }
                finally { listener.Stop(); }
            }
        }
        public static async Task<AccountSession> Ensure(string clientId, AccountVault vault, IProgress<WorkProgress> progress, CancellationToken cancel)
        {
            Guid id; if (!Guid.TryParse(clientId, out id)) throw new InvalidOperationException("Microsoft 로그인 연결 설정이 필요합니다. 설정에 포켓메이트용 공개 Client ID를 입력해주세요. 로그인 연결 안내.txt에 발급 방법이 있습니다.");
            AccountSession previous = vault.Read();
            if (previous != null && previous.ClientId == clientId && !String.IsNullOrEmpty(previous.AccessToken) && previous.ExpiresUtc > DateTime.UtcNow.AddMinutes(3)) return previous;
            Dictionary<string, object> microsoft = null;
            if (previous != null && previous.ClientId == clientId && !String.IsNullOrEmpty(previous.RefreshToken))
            {
                try { microsoft = await Net.Send("https://login.live.com/oauth20_token.srf", new Dictionary<string, string> {
                    {"client_id",clientId}, {"grant_type","refresh_token"}, {"refresh_token",previous.RefreshToken}, {"scope","XboxLive.signin offline_access"}}, null, true, cancel); }
                catch (ApiFailure error) { if (error.Status != 400 && error.Status != 401) throw; }
            }
            if (microsoft == null) microsoft = await Interactive(clientId, progress, cancel);
            string access = Json.Text(microsoft, "access_token");
            if (String.IsNullOrEmpty(access)) throw new InvalidOperationException("Microsoft 로그인 응답을 확인하지 못했습니다.");
            progress.Report(new WorkProgress("Xbox 계정과 Minecraft 소유 정보를 확인하는 중", 30));
            object xbox = await Net.Send("https://user.auth.xboxlive.com/user/authenticate", new {
                Properties = new { AuthMethod = "RPS", SiteName = "user.auth.xboxlive.com", RpsTicket = "d=" + access },
                RelyingParty = "http://auth.xboxlive.com", TokenType = "JWT" }, null, false, cancel);
            object xsts = await Net.Send("https://xsts.auth.xboxlive.com/xsts/authorize", new {
                Properties = new { SandboxId = "RETAIL", UserTokens = new[] { Json.Text(xbox,"Token") } },
                RelyingParty = "rp://api.minecraftservices.com/", TokenType = "JWT" }, null, false, cancel);
            object[] claims = Json.Array(Json.Get(Json.Get(xsts, "DisplayClaims"), "xui"));
            if (claims.Length == 0) throw new InvalidOperationException("Xbox 프로필을 확인하지 못했습니다. Xbox 계정 설정을 확인해주세요.");
            string uhs = Json.Text(claims[0], "uhs");
            object minecraft;
            try { minecraft = await Net.Send("https://api.minecraftservices.com/authentication/login_with_xbox", new { identityToken = "XBL3.0 x=" + uhs + ";" + Json.Text(xsts,"Token") }, null, false, cancel); }
            catch (ApiFailure error) { if (error.Status == 403) throw new InvalidOperationException("이 Client ID의 Minecraft API 사용 승인을 확인해주세요. Microsoft 앱 등록만으로는 접근이 허용되지 않을 수 있습니다. 로그인 연결 안내를 참고하세요."); throw; }
            string token = Json.Text(minecraft, "access_token");
            if (token.Length == 0) throw new InvalidOperationException("Minecraft 로그인 토큰을 확인하지 못했습니다.");
            object profile;
            try { profile = await Net.Send("https://api.minecraftservices.com/minecraft/profile", null, token, false, cancel); }
            catch (ApiFailure error) { if (error.Status == 404 || error.Status == 403) throw new InvalidOperationException("이 Microsoft 계정의 Minecraft Java Edition 보유 여부와 프로필 설정을 확인해주세요."); throw; }
            AccountSession session = new AccountSession { ClientId = clientId, Name = Json.Text(profile,"name"), Uuid = Json.Text(profile,"id"),
                Xuid = Json.Text(claims[0],"xid"), AccessToken = token, RefreshToken = Json.Text(microsoft,"refresh_token"),
                ExpiresUtc = DateTime.UtcNow.AddSeconds(Math.Max(60, Json.Number(minecraft,"expires_in"))) };
            if (session.RefreshToken.Length == 0 && previous != null) session.RefreshToken = previous.RefreshToken;
            if (session.Name.Length == 0 || session.Uuid.Length != 32) throw new InvalidOperationException("Minecraft Java 프로필이 올바르지 않습니다.");
            vault.Save(session); progress.Report(new WorkProgress(session.Name + " 님으로 로그인했습니다.", 100)); return session;
        }
    }
}
