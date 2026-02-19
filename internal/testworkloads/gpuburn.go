package testworkloads

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
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

// GPUBurnImages maps cluster architecture to the corresponding gpu-burn image.
var GPUBurnImages = map[string]string{
	"amd64": "quay.io/wabouham/gpu_burn_amd64:ubi9",
	"arm64": "quay.io/wabouham/gpu_burn_arm64:ubi9",
}

// GPUBurnWorkload implements the Workload interface for the gpu-burn stress test.
type GPUBurnWorkload struct {
	podName      string
	image        string
	duration     time.Duration
	gpuCount     int
	resources    corev1.ResourceRequirements
	nodeSelector map[string]string
	tolerations  []corev1.Toleration
}

// NewGPUBurn creates a GPUBurnWorkload with sensible defaults.
// image is required because gpu-burn images are architecture-specific;
// use GPUBurnImages[clusterArch] to select the right one.
func NewGPUBurn(podName, image string) *GPUBurnWorkload {
	glog.V(100).Infof("Creating GPUBurn workload: %s", podName)

	return &GPUBurnWorkload{
		podName:  podName,
		image:    image,
		duration: gpuBurnDefaultDuration,
		gpuCount: 1,
		resources: corev1.ResourceRequirements{
			Limits: corev1.ResourceList{
				"nvidia.com/gpu": resource.MustParse("1"),
			},
		},
		tolerations: []corev1.Toleration{
			{
				Key:      "nvidia.com/gpu",
				Effect:   corev1.TaintEffectNoSchedule,
				Operator: corev1.TolerationOpExists,
			},
		},
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

// WithResources sets custom resource requirements (use this for MIG profiles).
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

// WithGPUCount sets the number of GPU instances to expect in the success check.
// Use this for MIG workloads where multiple slices are requested.
func (g *GPUBurnWorkload) WithGPUCount(count int) *GPUBurnWorkload {
	g.gpuCount = count
	return g
}

// BuildPodSpec creates the pod specification for the GPUBurn workload.
// The gpu_burn binary is invoked directly — no ConfigMap or entrypoint script is needed.
func (g *GPUBurnWorkload) BuildPodSpec() (*corev1.Pod, error) {
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

	pod := NewUnprivilegedPod(
		g.podName,
		[]corev1.Container{container},
		g.nodeSelector,
		g.tolerations,
		map[string]string{"app": "gpu-burn-app"},
	)

	return pod, nil
}

// CheckSuccess validates gpu-burn output logs.
// It checks that each GPU index reported OK and that processing reached 100%.
func (g *GPUBurnWorkload) CheckSuccess(builder *Builder) error {
	glog.V(gpuparams.GpuLogLevel).Infof("Checking GPUBurn success criteria")

	logs, err := builder.GetFullLogs(GPUBurnContainerName)
	if err != nil {
		return fmt.Errorf("failed to get logs: %w", err)
	}

	for i := range g.gpuCount {
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
