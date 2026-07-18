import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Lock } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate("/admin");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#0A0A0B]">
      <div className="hidden lg:block relative overflow-hidden">
        <img src="https://images.pexels.com/photos/14734004/pexels-photo-14734004.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
          alt="port" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0B] via-[#0A0A0B]/50 to-transparent" />
        <div className="absolute bottom-12 left-12 right-12">
          <div className="label-caps mb-3">Executive Distribution</div>
          <h2 className="font-display text-3xl font-bold leading-tight">Admin Command Center</h2>
        </div>
      </div>

      <div className="flex items-center justify-center p-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="w-full max-w-sm">
          <div className="h-12 w-12 border border-[#4A7C94] flex items-center justify-center mb-8">
            <Lock size={20} className="text-[#4A7C94]" strokeWidth={1.5} />
          </div>
          <h1 className="font-display text-3xl font-bold mb-2">Sign in</h1>
          <p className="text-[#71717A] text-sm mb-8">Access the Executive Distribution dashboard.</p>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="label-caps block mb-2">Email</label>
              <input data-testid="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                required autoComplete="username"
                className="w-full bg-[#121214] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-4 py-3 text-sm transition-colors" />
            </div>
            <div>
              <label className="label-caps block mb-2">Password</label>
              <input data-testid="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required autoComplete="current-password"
                className="w-full bg-[#121214] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-4 py-3 text-sm transition-colors" />
            </div>

            {error && <div data-testid="login-error" className="text-sm text-red-400 bg-red-950/30 border border-red-900/40 px-4 py-3 rounded-sm">{error}</div>}

            <button data-testid="login-submit" type="submit" disabled={busy}
              className="w-full bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 transition-colors text-white px-6 py-3.5 rounded-sm font-medium flex items-center justify-center gap-2">
              {busy ? "Signing in…" : "Sign in"} {!busy && <ArrowRight size={16} />}
            </button>
          </form>

          <Link to="/" className="block text-center text-[#71717A] text-sm mt-8 hover:text-white transition-colors">← Back to website</Link>
        </motion.div>
      </div>
    </div>
  );
}
