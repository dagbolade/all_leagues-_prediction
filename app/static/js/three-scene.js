class FootballStadium {
    constructor() {
        this.init();
    }

    init() {
        // Get the container
        this.container = document.getElementById('threejs-container');

        // Set up scene
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(
            60,
            this.container.offsetWidth / this.container.offsetHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 10, 20);

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(this.container.offsetWidth, this.container.offsetHeight);
        this.container.appendChild(this.renderer.domElement);

        // Resize handling
        window.addEventListener('resize', () => this.onWindowResize(), false);

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(10, 20, 10);
        this.scene.add(directionalLight);

        // Create the football pitch
        this.createPitch();

        // Animate
        this.animate();
    }

    createPitch() {
        const pitchGeometry = new THREE.PlaneGeometry(20, 10);
        const pitchMaterial = new THREE.MeshPhongMaterial({ color: 0x228B22, side: THREE.DoubleSide });
        this.pitch = new THREE.Mesh(pitchGeometry, pitchMaterial);
        this.pitch.rotation.x = Math.PI / 2;
        this.scene.add(this.pitch);

        // Add white center line
        const lineGeometry = new THREE.PlaneGeometry(0.1, 10);
        const lineMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const centerLine = new THREE.Mesh(lineGeometry, lineMaterial);
        centerLine.rotation.x = Math.PI / 2;
        this.scene.add(centerLine);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        // Rotate the pitch slowly
        this.pitch.rotation.z += 0.0015;

        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        this.camera.aspect = this.container.offsetWidth / this.container.offsetHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.offsetWidth, this.container.offsetHeight);
    }
}
