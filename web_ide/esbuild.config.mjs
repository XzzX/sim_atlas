import esbuild from 'esbuild';

esbuild.build({
    entryPoints: ['js/index.tsx', 'js/index.html'],
    outdir: 'web',
    bundle: true, // Enable bundling
    format: 'esm', // Enable ES Modules
    splitting: true, // Enable code splitting for ESM
    minify: true, // Minify the output for production
    sourcemap: true, // Generate sourcemaps
    loader: {
        '.png': 'file', // Handle PNG images
        '.css': 'css', // Handle CSS files
        '.html': 'copy' // Handle HTML files
    },
    logLevel: 'info',
    entryNames: '[name]',
    assetNames: 'assets/[name]-[hash]',
    define: {
        'process.env.NODE_ENV': '"production"',
    },
    external: ['node_modules/*'], // Exclude specific modules from being bundled (e.g., node_modules)
    plugins: [],
    platform: 'browser', // Target the browser environment
}).then(() => {
    console.log('Build complete.');
}).catch(() => process.exit(1));