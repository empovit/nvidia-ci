package dra

const (
	DRADriverNamespace                  = "nvidia-dra-driver-gpu"
	DRADriverKubeletPluginDaemonSetName = "nvidia-dra-driver-gpu-kubelet-plugin"
	DRAComponentLabelKey                = "nvidia-dra-driver-gpu-component"
	DRAComponentController              = "controller"
	DRAComponentKubeletPlugin           = "kubelet-plugin"
	DRAAPIGroup                         = "resource.k8s.io"
	DRADeviceClassesResource            = "deviceclasses"
)
