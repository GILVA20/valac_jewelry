module.exports = {
  content: [
    "./valac_jewelry/templates/**/*.html",
    "./static/**/*.js"  // Ajusta según donde tengas tus archivos JS si los usas.
  ],
  theme: {
    extend: {
        colors: {
          'cartier-gold': '#A67C00',
          'dark-gray': '#333333',
          'light-gray': '#B0B0B0',
          'white': '#FFFFFF',
          'black': '#000000',
        },
    },
},
  plugins: [],
}

