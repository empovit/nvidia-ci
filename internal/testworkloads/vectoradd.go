package testworkloads

import (
	"fmt"
	"strings"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/pod"
	corev1 "k8s.io/api/core/v1"
)

const (
	// DefaultImage is the default container image for VectorAdd workload.
	DefaultImage = "nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0-ubi8"

	// ContainerName is the name of the VectorAdd container.
	ContainerName = "vectoradd-ctr"

	// SuccessIndicator is the string that indicates successful completion in logs.
	SuccessIndicator = "Test PASSED"
)

// VectorAddWorkload configures a CUDA vector addition sample workload.
type VectorAddWorkload struct {
	podName        string
	image          string
	command        []string
	resources      corev1.ResourceRequirements
	nodeSelector   map[string]string
	tolerations    []corev1.Toleration
	resourceClaims []corev1.PodResourceClaim
}

// NewVectorAdd creates a VectorAdd workload with sensible defaults.
func NewVectorAdd(podName string) *VectorAddWorkload {
	glog.V(100).Infof("Creating VectorAdd workload: %s", podName)

	return &VectorAddWorkload{
		podName:     podName,
		image:       DefaultImage,
		resources:   defaultGPUResources(),
		tolerations: defaultGPUTolerations(),
	}
}

// WithImage sets a custom container image.
func (v *VectorAddWorkload) WithImage(image string) *VectorAddWorkload {
	v.image = image
	return v
}

// WithCommand sets a custom command for the container.
func (v *VectorAddWorkload) WithCommand(command []string) *VectorAddWorkload {
	v.command = command
	return v
}

// WithResources sets custom resource requirements.
func (v *VectorAddWorkload) WithResources(resources corev1.ResourceRequirements) *VectorAddWorkload {
	v.resources = resources
	return v
}

// WithNodeSelector sets a custom node selector.
func (v *VectorAddWorkload) WithNodeSelector(selector map[string]string) *VectorAddWorkload {
	v.nodeSelector = selector
	return v
}

// WithTolerations sets custom tolerations.
func (v *VectorAddWorkload) WithTolerations(tolerations []corev1.Toleration) *VectorAddWorkload {
	v.tolerations = tolerations
	return v
}

// WithResourceClaims sets resource claims for DRA support.
func (v *VectorAddWorkload) WithResourceClaims(claims []corev1.PodResourceClaim) *VectorAddWorkload {
	v.resourceClaims = claims
	return v
}

// Create deploys the workload pod to the cluster and returns a Workload for lifecycle management.
func (v *VectorAddWorkload) Create(apiClient *clients.Settings, namespace string) (*Workload, error) {
	podSpec, err := v.buildPodSpec()
	if err != nil {
		return nil, err
	}

	return newWorkload(apiClient, namespace, podSpec, vectorAddSuccessCheck)
}

func (v *VectorAddWorkload) buildPodSpec() (*corev1.Pod, error) {
	glog.V(gpuparams.GpuLogLevel).Infof("Building pod spec for VectorAdd workload: %s", v.podName)

	if v.podName == "" {
		return nil, fmt.Errorf("pod name cannot be empty")
	}

	if v.image == "" {
		return nil, fmt.Errorf("container image cannot be empty")
	}

	container := NewUnprivilegedContainer(ContainerName, v.image, v.resources)

	if len(v.command) > 0 {
		container.Command = v.command
	}

	p := NewUnprivilegedPod(
		v.podName,
		[]corev1.Container{container},
		v.nodeSelector,
		v.tolerations,
		map[string]string{"app": "vectoradd-app"},
	)

	if len(v.resourceClaims) > 0 {
		p.Spec.ResourceClaims = v.resourceClaims
	}

	return p, nil
}

func vectorAddSuccessCheck(pb *pod.Builder) error {
	logs, err := pb.GetFullLog(ContainerName)
	if err != nil {
		return fmt.Errorf("failed to get logs: %w", err)
	}

	if !strings.Contains(logs, SuccessIndicator) {
		return fmt.Errorf("logs do not contain success indicator '%s'", SuccessIndicator)
	}

	return nil
}
