def duplicate_icmp_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-icmp-check', kwargs={'pk': npk}))



def duplicate_graphite_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-graphite-check', kwargs={'pk': npk}))


def duplicate_jenkins_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-jenkins-check', kwargs={'pk': npk}))
