package testworkloads

import (
	"sort"

	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/nvidiagpu"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/utils/ptr"
)

func supportedArchitectures(images map[string]string) []string {
	archs := make([]string, 0, len(images))
	for arch := range images {
		archs = append(archs, arch)
	}

	sort.Strings(archs)

	return archs
}

func defaultGPUResources() corev1.ResourceRequirements {
	return corev1.ResourceRequirements{
		Limits: corev1.ResourceList{
			nvidiagpu.GPUResourceName: resource.MustParse("1"),
		},
	}
}

func defaultGPUTolerations() []corev1.Toleration {
	return []corev1.Toleration{
		{
			Key:      nvidiagpu.GPUTolerationKey,
			Effect:   corev1.TaintEffectNoSchedule,
			Operator: corev1.TolerationOpExists,
		},
	}
}

// NewUnprivilegedPod creates a pod with security best practices.
// Accepts a slice of containers to support both single and multi-container workloads.
func NewUnprivilegedPod(
	podName string,
	containers []corev1.Container,
	nodeSelector map[string]string,
	tolerations []corev1.Toleration,
	labels map[string]string,
) *corev1.Pod {
	return &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:   podName,
			Labels: labels,
		},
		Spec: corev1.PodSpec{
			RestartPolicy: corev1.RestartPolicyNever,
			SecurityContext: &corev1.PodSecurityContext{
				RunAsNonRoot:   ptr.To(true),
				SeccompProfile: &corev1.SeccompProfile{Type: corev1.SeccompProfileTypeRuntimeDefault},
			},
			Tolerations:  tolerations,
			Containers:   containers,
			NodeSelector: nodeSelector,
		},
	}
}

// NewUnprivilegedContainer creates a container with security best practices.
func NewUnprivilegedContainer(
	name string,
	image string,
	resources corev1.ResourceRequirements,
) corev1.Container {
	return corev1.Container{
		Name:            name,
		Image:           image,
		ImagePullPolicy: corev1.PullAlways,
		SecurityContext: &corev1.SecurityContext{
			AllowPrivilegeEscalation: ptr.To(false),
			Capabilities: &corev1.Capabilities{
				Drop: []corev1.Capability{"ALL"},
			},
		},
		Resources: resources,
	}
}
