// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
/**
 * Image Zoom and Pan functionality for Vedfolnir
 * Allows users to zoom in/out and pan around images for better review
 */
class ImageZoom {
    constructor(container) {
        this.container = container;
        this.wrapper = container.querySelector('.image-zoom-wrapper');
        this.img = container.querySelector('.image-zoomable');
        this.zoomInBtn = container.querySelector('.zoom-in');
        this.zoomOutBtn = container.querySelector('.zoom-out');
        this.zoomResetBtn = container.querySelector('.zoom-reset');
        
        this.scale = 1;
        this.panning = false;
        this.pointX = 0;
        this.pointY = 0;
        this.start = { x: 0, y: 0 };
        
        this.init();
    }
    
    init() {
        // Set initial state
        this.setTransform();
        
        // Add event listeners for zoom buttons
        this.zoomInBtn.addEventListener('click', () => this.zoomIn());
        this.zoomOutBtn.addEventListener('click', () => this.zoomOut());
        this.zoomResetBtn.addEventListener('click', () => this.resetZoom());
        
        // Mouse wheel zoom
        this.wrapper.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY * -0.01;
            this.zoom(delta);
        });
        
        // Mouse events for panning
        this.wrapper.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.panning = true;
            this.start = { x: e.clientX - this.pointX, y: e.clientY - this.pointY };
            this.wrapper.style.cursor = 'grabbing';
        });
        
        this.wrapper.addEventListener('mouseup', () => {
            this.panning = false;
            this.wrapper.style.cursor = 'move';
        });
        
        this.wrapper.addEventListener('mouseleave', () => {
            this.panning = false;
            this.wrapper.style.cursor = 'move';
        });
        
        this.wrapper.addEventListener('mousemove', (e) => {
            if (!this.panning) return;
            e.preventDefault();
            this.pointX = e.clientX - this.start.x;
            this.pointY = e.clientY - this.start.y;
            this.setTransform();
        });
        
        // Touch events for mobile
        this.wrapper.addEventListener('touchstart', (e) => {
            e.preventDefault();
            if (e.touches.length === 1) {
                this.panning = true;
                this.start = { 
                    x: e.touches[0].clientX - this.pointX, 
                    y: e.touches[0].clientY - this.pointY 
                };
            }
        });
        
        this.wrapper.addEventListener('touchend', () => {
            this.panning = false;
        });
        
        this.wrapper.addEventListener('touchmove', (e) => {
            if (!this.panning || e.touches.length !== 1) return;
            e.preventDefault();
            this.pointX = e.touches[0].clientX - this.start.x;
            this.pointY = e.touches[0].clientY - this.start.y;
            this.setTransform();
        });
        
        // Double click to reset
        this.wrapper.addEventListener('dblclick', () => {
            this.resetZoom();
        });
    }
    
    zoomIn() {
        this.zoom(0.1);
    }
    
    zoomOut() {
        this.zoom(-0.1);
    }
    
    zoom(delta) {
        const newScale = this.scale + delta;
        // Limit zoom level between 0.5 and 4
        if (newScale >= 0.5 && newScale <= 4) {
            this.scale = newScale;
            this.setTransform();
        }
    }
    
    resetZoom() {
        this.scale = 1;
        this.pointX = 0;
        this.pointY = 0;
        this.setTransform();
    }
    
    setTransform() {
        this.img.style.transform = `translate(${this.pointX}px, ${this.pointY}px) scale(${this.scale})`;
    }
}

// Initialize image zoom functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const imageContainers = document.querySelectorAll('.image-container');
    imageContainers.forEach(container => {
        new ImageZoom(container);
    });
});