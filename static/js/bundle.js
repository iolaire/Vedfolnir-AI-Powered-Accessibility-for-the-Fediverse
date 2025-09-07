#!/usr/bin/env node

/**
 * Vedfolnir JavaScript Bundler
 * 
 * This script bundles and optimizes JavaScript files for better performance:
 * - Combines multiple files into logical bundles
 * - Minifies code for production
 * - Generates source maps for debugging
 * - Creates versioned files for caching
 */

const fs = require('fs-extra');
const path = require('path');
const { minify } = require('terser');

// Bundle configurations
const bundles = {
    // Core bundle - Essential for all pages
    'core': {
        files: [
            'csrf-handler.js',
            'error_handler.js',
            'navigation.js',
            'platform_context_refresh.js',
            'session-sync.js',
            'progress-bar-utils.js',
            'progress-bar-init.js'
        ],
        description: 'Core functionality for all pages'
    },
    
    // WebSocket bundle - Real-time communication
    'websocket': {
        files: [
            'websocket-transport-optimizer.js',
            'websocket-bundle.js',
            'websocket-client-factory.js',
            'websocket-client.js',
            'websocket-keepalive.js',
            'websocket-connection-status.js',
            'websocket-performance-monitor.js'
        ],
        description: 'WebSocket functionality bundle'
    },
    
    // Notification bundle - Unified notification system
    'notification': {
        files: [
            'notification-ui-renderer.js',
            'page_notification_integrator.js',
            'websocket-enhanced-client-error-handler.js',
            'websocket-enhanced-error-handler.js'
        ],
        description: 'Unified notification system'
    },
    
    // Admin bundle - Admin-specific functionality
    'admin': {
        files: [
            'admin.js',
            'user_management.js',
            'websocket-debug.js',
            'websocket-debug-diagnostics.js'
        ],
        description: 'Admin interface functionality'
    },
    
    // Platform bundle - Platform management
    'platform': {
        files: [
            'platform_management.js',
            'platform_management_websocket.js'
        ],
        description: 'Platform management functionality'
    },
    
    // Caption bundle - Caption generation
    'caption': {
        files: [
            'caption_generation.js',
            'review.js',
            'image-zoom.js'
        ],
        description: 'Caption generation and review functionality'
    },
    
    // App bundle - Main application logic
    'app': {
        files: [
            'app.js'
        ],
        description: 'Main application logic'
    }
};

// Utility functions
async function readFile(filePath) {
    try {
        return await fs.readFile(filePath, 'utf8');
    } catch (error) {
        console.error(`Error reading file ${filePath}:`, error);
        return null;
    }
}

async function writeFile(filePath, content) {
    try {
        await fs.writeFile(filePath, content, 'utf8');
        console.log(`✓ Generated ${filePath}`);
    } catch (error) {
        console.error(`Error writing file ${filePath}:`, error);
    }
}

async function ensureDir(dirPath) {
    try {
        await fs.ensureDir(dirPath);
    } catch (error) {
        console.error(`Error creating directory ${dirPath}:`, error);
    }
}

function generateBanner(bundleName, config) {
    const timestamp = new Date().toISOString();
    return `/**
 * Vedfolnir ${bundleName.charAt(0).toUpperCase() + bundleName.slice(1)} Bundle
 * ${config.description}
 * Generated: ${timestamp}
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 */
`;
}

function generateVersion() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `${timestamp}-${random}`;
}

async function createBundle(bundleName, config, minify = false) {
    console.log(`\n📦 Creating ${bundleName} bundle...`);
    
    const jsDir = path.dirname(__filename);
    const distDir = path.join(jsDir, 'dist');
    const bundleDir = path.join(distDir, bundleName);
    
    await ensureDir(bundleDir);
    
    // Read all files
    const fileContents = [];
    for (const file of config.files) {
        const filePath = path.join(jsDir, file);
        const content = await readFile(filePath);
        if (content) {
            fileContents.push({
                name: file,
                content: content
            });
        }
    }
    
    if (fileContents.length === 0) {
        console.log(`⚠️  No files found for ${bundleName} bundle`);
        return;
    }
    
    // Combine files with banner
    const banner = generateBanner(bundleName, config);
    let combinedContent = banner;
    
    // Add each file with header
    for (const file of fileContents) {
        combinedContent += `\n\n// =============================================================================\n`;
        combinedContent += `// File: ${file.name}\n`;
        combinedContent += `// =============================================================================\n\n`;
        combinedContent += file.content;
    }
    
    // Generate version
    const version = generateVersion();
    
    // Write unminified version
    const unminifiedPath = path.join(bundleDir, `${bundleName}.js`);
    await writeFile(unminifiedPath, combinedContent);
    
    // Write versioned unminified version
    const versionedPath = path.join(bundleDir, `${bundleName}-${version}.js`);
    await writeFile(versionedPath, combinedContent);
    
    // Minify if requested
    if (minify) {
        console.log(`🗜️  Minifying ${bundleName} bundle...`);
        try {
            const minifiedResult = await minify(combinedContent, {
                ecma: 2020,
                compress: {
                    drop_console: false, // Keep console logs for debugging
                    drop_debugger: true,
                    pure_funcs: ['console.debug']
                },
                mangle: {
                    toplevel: false,
                    reserved: ['require', 'module', 'exports']
                },
                format: {
                    comments: false
                }
            });
            
            if (minifiedResult.code) {
                // Write minified version
                const minifiedPath = path.join(bundleDir, `${bundleName}.min.js`);
                await writeFile(minifiedPath, minifiedResult.code);
                
                // Write versioned minified version
                const versionedMinifiedPath = path.join(bundleDir, `${bundleName}-${version}.min.js`);
                await writeFile(versionedMinifiedPath, minifiedResult.code);
            }
        } catch (error) {
            console.error(`Error minifying ${bundleName} bundle:`, error);
        }
    }
    
    // Create bundle manifest
    const manifest = {
        name: bundleName,
        version: version,
        description: config.description,
        files: config.files,
        generated: new Date().toISOString(),
        size: {
            unminified: combinedContent.length,
            minified: minifiedResult ? minifiedResult.code.length : null
        }
    };
    
    const manifestPath = path.join(bundleDir, 'manifest.json');
    await writeFile(manifestPath, JSON.stringify(manifest, null, 2));
    
    console.log(`✓ ${bundleName} bundle created successfully`);
}

async function generateBundleManifest() {
    console.log('\n📋 Generating bundle manifest...');
    
    const distDir = path.join(path.dirname(__filename), 'dist');
    const manifest = {
        generated: new Date().toISOString(),
        bundles: {},
        totalSize: 0
    };
    
    // Read individual bundle manifests
    for (const bundleName of Object.keys(bundles)) {
        const manifestPath = path.join(distDir, bundleName, 'manifest.json');
        if (await fs.pathExists(manifestPath)) {
            const bundleManifest = await fs.readJson(manifestPath);
            manifest.bundles[bundleName] = bundleManifest;
            manifest.totalSize += bundleManifest.size.unminified;
        }
    }
    
    const mainManifestPath = path.join(distDir, 'bundle-manifest.json');
    await writeFile(mainManifestPath, JSON.stringify(manifest, null, 2));
    
    console.log(`✓ Bundle manifest generated`);
    console.log(`📊 Total bundle size: ${(manifest.totalSize / 1024 / 1024).toFixed(2)} MB`);
}

async function createOptimizedBaseTemplate() {
    console.log('\n📄 Creating optimized base template...');
    
    const jsDir = path.dirname(__filename);
    const templateDir = path.join(jsDir, '..', '..', 'templates');
    
    // Read current base.html
    const baseHtmlPath = path.join(templateDir, 'base.html');
    const baseHtml = await readFile(baseHtmlPath);
    
    if (!baseHtml) {
        console.error('Could not read base.html');
        return;
    }
    
    // Create optimized template
    const optimizedTemplate = baseHtml.replace(
        /<!-- JavaScript includes start -->[\s\S]*<!-- JavaScript includes end -->/,
        `<!-- Optimized JavaScript Bundles -->
    <!-- Core Bundle - Essential for all pages -->
    <script src="{{ url_for('static', filename='js/dist/core/core.min.js', v=BUNDLE_VERSION) }}" onerror="console.warn('Core bundle failed to load')"></script>
    
    <!-- WebSocket Bundle - Real-time communication -->
    <script src="{{ url_for('static', filename='js/dist/websocket/websocket.min.js', v=BUNDLE_VERSION) }}" onerror="console.warn('WebSocket bundle failed to load')"></script>
    
    <!-- Notification Bundle - Unified notification system -->
    <script src="{{ url_for('static', filename='js/dist/notification/notification.min.js', v=BUNDLE_VERSION) }}" onerror="console.warn('Notification bundle failed to load')"></script>
    
    <!-- App Bundle - Main application logic -->
    <script src="{{ url_for('static', filename='js/dist/app/app.min.js', v=BUNDLE_VERSION) }}" onerror="console.warn('App bundle failed to load')"></script>
    
    <!-- Page-specific bundles will be loaded as needed -->
    {% block page_scripts %}{% endblock %}`
    );
    
    // Write optimized template
    const optimizedPath = path.join(templateDir, 'base-optimized.html');
    await writeFile(optimizedPath, optimizedTemplate);
    
    console.log('✓ Optimized base template created');
}

async function main() {
    console.log('🚀 Starting Vedfolnir JavaScript bundler...');
    
    const args = process.argv.slice(2);
    const minify = args.includes('--prod') || args.includes('--minify');
    const analyze = args.includes('--analyze');
    
    console.log(`Mode: ${minify ? 'Production (minified)' : 'Development'}`);
    
    // Create all bundles
    for (const [bundleName, config] of Object.entries(bundles)) {
        await createBundle(bundleName, config, minify);
    }
    
    // Generate bundle manifest
    await generateBundleManifest();
    
    // Create optimized template
    await createOptimizedBaseTemplate();
    
    console.log('\n🎉 JavaScript bundling completed!');
    console.log('\n📁 Generated files:');
    console.log('  - static/js/dist/[bundle]/[bundle].js (unminified)');
    console.log('  - static/js/dist/[bundle]/[bundle].min.js (minified)');
    console.log('  - static/js/dist/[bundle]/manifest.json (bundle info)');
    console.log('  - static/js/dist/bundle-manifest.json (overall manifest)');
    console.log('  - templates/base-optimized.html (optimized template)');
    
    console.log('\n📋 Next steps:');
    console.log('  1. Test the optimized bundles');
    console.log('  2. Update base.html to use bundled version');
    console.log('  3. Update page-specific scripts to use bundles');
    console.log('  4. Test all functionality thoroughly');
}

// Run the bundler
main().catch(error => {
    console.error('Bundler failed:', error);
    process.exit(1);
});