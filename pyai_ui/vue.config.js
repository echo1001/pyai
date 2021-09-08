module.exports = {
  devServer: {
    public: "192.168.1.18:8080",
    proxy: {
      '/api': {
        target: 'http://192.168.1.18:5000',
        ws: true,
        changeOrigin: true
      },
    }
  }
}