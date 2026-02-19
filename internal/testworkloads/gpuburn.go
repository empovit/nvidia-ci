package testworkloads

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/pod"
	corev1 "k8s.io/api/core/v1"
)

const (
	// GPUBurnContainerName is the name of the gpu-burn container.
	GPUBurnContainerName = "gpu-burn-ctr"

	// GPUBurnNamespace is the default namespace for gpu-burn workloads.
	GPUBurnNamespace = "test-gpu-burn"

	// GPUBurnPodName is the default pod name for gpu-burn workloads.
	GPUBurnPodName = "gpu-burn-pod"

	// GPUBurnPodLabel is the label selector for gpu-burn pods.
	GPUBurnPodLabel = "app=gpu-burn-app"

	gpuBurnDefaultDuration = 300 * time.Second
)

// gpuBurnImages maps cluster architecture to the corresponding gpu-burn image.
var gpuBurnImages = map[string]string{
	"amd64": "quay.io/wabouham/gpu_burn_amd64:ubi9",
	"arm64": "quay.io/wabouham/gpu_burn_arm64:ubi9",
}

// DefaultGPUBurnImageForArch returns the default gpu-burn container image for the given cluster architecture.
// Returns an error if the architecture is not supported.
func DefaultGPUBurnImageForArch(arch string) (string, error) {
	image, ok := gpuBurnImages[arch]
	if !ok {
		return "", fmt.Errorf("unsupported architecture %q for gpu-burn; supported: %v", arch, supportedArchitectures(gpuBurnImages))
	}

	return image, nil
}

// GPUBurnWorkload configures a gpu-burn stress test workload.
type GPUBurnWorkload struct {
	podName      string
	image        string
	duration     time.Duration
	resources    corev1.ResourceRequirements
	nodeSelector map[string]string
	tolerations  []corev1.Toleration
}

// NewGPUBurn creates a GPUBurnWorkload with sensible defaults.
// image is required because gpu-burn images are architecture-specific;
// use DefaultGPUBurnImageForArch to select the right one.
func NewGPUBurn(podName, image string) *GPUBurnWorkload {
	glog.V(100).Infof("Creating GPUBurn workload: %s", podName)

	return &GPUBurnWorkload{
		podName:     podName,
		image:       image,
		duration:    gpuBurnDefaultDuration,
		resources:   defaultGPUResources(),
		tolerations: defaultGPUTolerations(),
	}
}

// WithImage sets a custom container image.
func (g *GPUBurnWorkload) WithImage(image string) *GPUBurnWorkload {
	g.image = image
	return g
}

// WithDuration sets how long gpu_burn runs.
func (g *GPUBurnWorkload) WithDuration(d time.Duration) *GPUBurnWorkload {
	g.duration = d
	return g
}

// WithResources sets custom resource requirements.
func (g *GPUBurnWorkload) WithResources(resources corev1.ResourceRequirements) *GPUBurnWorkload {
	g.resources = resources
	return g
}

// WithNodeSelector sets a custom node selector.
func (g *GPUBurnWorkload) WithNodeSelector(selector map[string]string) *GPUBurnWorkload {
	g.nodeSelector = selector
	return g
}

// WithTolerations sets custom tolerations.
func (g *GPUBurnWorkload) WithTolerations(tolerations []corev1.Toleration) *GPUBurnWorkload {
	g.tolerations = tolerations
	return g
}

// Create deploys the workload pod to the cluster and returns a Workload for lifecycle management.
func (g *GPUBurnWorkload) Create(apiClient *clients.Settings, namespace string) (*Workload, error) {
	podSpec, err := g.buildPodSpec()
	if err != nil {
		return nil, err
	}

	return newWorkload(apiClient, namespace, podSpec, gpuBurnSuccessCheck(nvidiaGPUCount(g.resources)))
}

func (g *GPUBurnWorkload) buildPodSpec() (*corev1.Pod, error) {
	glog.V(gpuparams.GpuLogLevel).Infof("Building pod spec for GPUBurn workload: %s", g.podName)

	if g.podName == "" {
		return nil, fmt.Errorf("pod name cannot be empty")
	}

	if g.image == "" {
		return nil, fmt.Errorf("container image cannot be empty")
	}

	seconds := int(g.duration.Seconds())
	container := NewUnprivilegedContainer(GPUBurnContainerName, g.image, g.resources)
	container.Command = []string{"./gpu_burn", strconv.Itoa(seconds)}

	p := NewUnprivilegedPod(
		g.podName,
		[]corev1.Container{container},
		g.nodeSelector,
		g.tolerations,
		map[string]string{"app": "gpu-burn-app"},
	)

	return p, nil
}

// nvidiaGPUCount returns the total number of nvidia.com/* resources requested.
func nvidiaGPUCount(resources corev1.ResourceRequirements) int {
	count := 0
	for name, qty := range resources.Limits {
		if strings.HasPrefix(string(name), "nvidia.com/") {
			count += int(qty.Value())
		}
	}

	if count == 0 {
		return 1
	}

	return count
}

func gpuBurnSuccessCheck(count int) func(*pod.Builder) error {
	return func(pb *pod.Builder) error {
		logs, err := pb.GetFullLog(GPUBurnContainerName)
		if err != nil {
			return fmt.Errorf("failed to get logs: %w", err)
		}

		for i := range count {
			expected := fmt.Sprintf("GPU %d: OK", i)
			if !strings.Contains(logs, expected) {
				return fmt.Errorf("logs do not contain %q", expected)
			}
		}

		if !strings.Contains(logs, "100.0%  proc'd:") {
			return fmt.Errorf("logs do not contain \"100.0%%  proc'd:\"")
		}

		return nil
	}
}
