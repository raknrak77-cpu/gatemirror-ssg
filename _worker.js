export default {
  async fetch(request, env, ctx) {
    // Worker'a yönlendir
    return env.R2_PROXY.fetch(request);
  }
};
